"""
AutoOps AI — CSV Export Tool.

Reads an uploaded CSV/Excel file, performs comprehensive analysis (statistics,
distributions, correlations, outliers, data quality), and generates a
multi-sheet Excel output file. Handles edge cases robustly:
  - Empty DataFrames, single-column files, non-numeric data
  - Large files (sampled analysis for 100k+ rows)
  - Datetime columns (auto-detected and summarized)
  - Mixed types, nulls, duplicates
"""

import os
import uuid
import logging
from typing import Any, Dict
from datetime import datetime

from .base_tool import BaseTool

logger = logging.getLogger("autoops.tools.csv_export")

# Max rows to include in source data sheet (prevents massive Excel files)
MAX_SOURCE_ROWS = 1000
# Max rows before we sample for correlation/distribution analysis
LARGE_FILE_THRESHOLD = 100_000


class CSVExportTool(BaseTool):
    name = "csv_export_tool"
    description = "Analyzes CSV/Excel files and generates comprehensive analysis output"

    def run(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a CSV/Excel file and produce a multi-sheet Excel analysis.

        input_data:
            - file_path: Path to the source file (CSV, XLSX, XLS)
            - llm_summary: LLM agent's analysis summary
            - input_text: User's original prompt

        context:
            - workflow_id: Current workflow ID
            - user_id: Current user ID
            - event_loop: FastAPI event loop for async DB operations

        Returns:
            - output_file_path: Path to the generated analysis Excel
            - analysis: Dict of analysis results
        """
        import pandas as pd
        from .csv_tool import read_csv_safe

        file_path = input_data.get("file_path", "")

        if not file_path or not os.path.exists(file_path):
            return {
                "status": "failed",
                "error": f"File not found: {file_path}",
            }

        try:
            df, encoding = read_csv_safe(file_path)
            logger.info(
                f"CSV Export: loaded {file_path} "
                f"({len(df)} rows, {len(df.columns)} cols, encoding={encoding})"
            )

            # Handle empty dataframe
            if df.empty:
                return {
                    "status": "completed",
                    "message": "File is empty — no data to analyze",
                    "analysis": {
                        "total_rows": 0,
                        "total_columns": len(df.columns),
                        "columns": list(df.columns),
                    },
                }

            original_name = os.path.basename(file_path)

            # ── Classify columns ──
            # Try to convert object columns that look like numbers
            for col in df.select_dtypes(include=["object"]).columns:
                try:
                    converted = pd.to_numeric(df[col], errors="coerce")
                    if converted.notna().sum() > len(df) * 0.5:
                        df[col] = converted
                except Exception:
                    pass

            # Try to parse datetime columns
            datetime_cols = []
            for col in df.select_dtypes(include=["object"]).columns:
                try:
                    parsed = pd.to_datetime(df[col], errors="coerce", infer_datetime_format=True)
                    if parsed.notna().sum() > len(df) * 0.5:
                        df[col] = parsed
                        datetime_cols.append(col)
                except Exception:
                    pass

            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
            cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
            dt_cols = df.select_dtypes(include=["datetime"]).columns.tolist()
            bool_cols = df.select_dtypes(include=["bool"]).columns.tolist()

            is_large = len(df) > LARGE_FILE_THRESHOLD

            # ── Sheet 1: Summary Statistics ──
            summary_rows = [
                {"Metric": "Total Rows", "Value": len(df)},
                {"Metric": "Total Columns", "Value": len(df.columns)},
                {"Metric": "Numeric Columns", "Value": len(numeric_cols)},
                {"Metric": "Categorical Columns", "Value": len(cat_cols)},
                {"Metric": "Datetime Columns", "Value": len(dt_cols)},
                {"Metric": "Boolean Columns", "Value": len(bool_cols)},
                {"Metric": "Total Missing Values", "Value": int(df.isnull().sum().sum())},
                {"Metric": "Missing Value %", "Value": round(df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100, 2) if len(df) > 0 and len(df.columns) > 0 else 0},
                {"Metric": "Duplicate Rows", "Value": int(df.duplicated().sum())},
                {"Metric": "Duplicate Row %", "Value": round(df.duplicated().sum() / len(df) * 100, 2) if len(df) > 0 else 0},
                {"Metric": "Memory Usage (KB)", "Value": round(df.memory_usage(deep=True).sum() / 1024, 2)},
                {"Metric": "Source File", "Value": original_name},
                {"Metric": "Encoding Detected", "Value": encoding},
                {"Metric": "Large File Mode", "Value": "Yes" if is_large else "No"},
                {"Metric": "Analysis Timestamp", "Value": datetime.utcnow().isoformat() + "Z"},
            ]
            summary_df = pd.DataFrame(summary_rows)

            # ── Sheet 2: Column-level Analysis ──
            col_analysis = []
            for col in df.columns:
                info = {
                    "Column": col,
                    "Type": str(df[col].dtype),
                    "Non-Null Count": int(df[col].count()),
                    "Null Count": int(df[col].isnull().sum()),
                    "Null %": round(df[col].isnull().sum() / len(df) * 100, 1) if len(df) > 0 else 0,
                    "Unique Values": int(df[col].nunique()),
                    "Unique %": round(df[col].nunique() / len(df) * 100, 1) if len(df) > 0 else 0,
                }

                if col in numeric_cols:
                    series = df[col].dropna()
                    if not series.empty:
                        info["Min"] = series.min()
                        info["Max"] = series.max()
                        info["Mean"] = round(float(series.mean()), 4)
                        info["Median"] = round(float(series.median()), 4)
                        info["Std Dev"] = round(float(series.std()), 4)
                        info["Skewness"] = round(float(series.skew()), 4) if len(series) > 2 else None
                        # Outlier detection (IQR method)
                        q1 = series.quantile(0.25)
                        q3 = series.quantile(0.75)
                        iqr = q3 - q1
                        outlier_count = int(((series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)).sum())
                        info["Outliers (IQR)"] = outlier_count
                elif col in cat_cols:
                    top_val = df[col].mode().iloc[0] if not df[col].mode().empty else None
                    info["Top Value"] = str(top_val) if top_val is not None else None
                    info["Top Frequency"] = int(df[col].value_counts().iloc[0]) if not df[col].value_counts().empty else 0
                elif col in dt_cols:
                    series = df[col].dropna()
                    if not series.empty:
                        info["Earliest"] = str(series.min())
                        info["Latest"] = str(series.max())
                        info["Date Range"] = str(series.max() - series.min())

                col_analysis.append(info)

            col_df = pd.DataFrame(col_analysis)

            # ── Sheet 3: Numeric Correlations ──
            corr_df = None
            if len(numeric_cols) >= 2:
                sample = df[numeric_cols].sample(min(len(df), 50000), random_state=42) if is_large else df[numeric_cols]
                corr_df = sample.corr().round(3)

            # ── Sheet 4: Value Distributions for Categorical ──
            dist_rows = []
            for col in cat_cols[:15]:
                vc = df[col].value_counts().head(15)
                for val, count in vc.items():
                    dist_rows.append({
                        "Column": col,
                        "Value": str(val)[:100],  # Truncate long values
                        "Count": count,
                        "Percentage": round(count / len(df) * 100, 2) if len(df) > 0 else 0,
                    })
            dist_df = pd.DataFrame(dist_rows) if dist_rows else None

            # ── Sheet 5: Data Quality Report ──
            quality_rows = []
            for col in df.columns:
                null_pct = df[col].isnull().sum() / len(df) * 100 if len(df) > 0 else 0
                unique_pct = df[col].nunique() / len(df) * 100 if len(df) > 0 else 0

                # Quality score (0-100)
                completeness = 100 - null_pct
                has_variation = min(unique_pct * 10, 100) if unique_pct < 100 else 100
                quality_score = round((completeness * 0.7 + has_variation * 0.3), 1)

                issues = []
                if null_pct > 50:
                    issues.append("High nulls")
                if null_pct > 0 and null_pct <= 50:
                    issues.append("Some nulls")
                if unique_pct == 0:
                    issues.append("No variation")
                if unique_pct >= 99 and col in cat_cols:
                    issues.append("Possible ID column")

                quality_rows.append({
                    "Column": col,
                    "Completeness %": round(completeness, 1),
                    "Unique %": round(unique_pct, 1),
                    "Quality Score": quality_score,
                    "Issues": "; ".join(issues) if issues else "None",
                })
            quality_df = pd.DataFrame(quality_rows)

            # ── Write output Excel file ──
            from ..core.config import settings
            os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

            output_name = f"analysis_{uuid.uuid4().hex[:8]}_{original_name}"
            try:
                import openpyxl  # noqa: F401
                output_name = output_name.rsplit(".", 1)[0] + ".xlsx"
                output_path = os.path.join(settings.UPLOAD_DIR, output_name)

                with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                    summary_df.to_excel(writer, sheet_name="Summary", index=False)
                    col_df.to_excel(writer, sheet_name="Column Analysis", index=False)
                    quality_df.to_excel(writer, sheet_name="Data Quality", index=False)
                    if corr_df is not None:
                        corr_df.to_excel(writer, sheet_name="Correlations")
                    if dist_df is not None:
                        dist_df.to_excel(writer, sheet_name="Distributions", index=False)
                    # Include source data (capped)
                    df.head(MAX_SOURCE_ROWS).to_excel(
                        writer, sheet_name=f"Source Data (first {min(len(df), MAX_SOURCE_ROWS)})", index=False
                    )

                logger.info(f"Analysis Excel written: {output_path}")

            except ImportError:
                # Fallback: write as CSV
                output_name = output_name.rsplit(".", 1)[0] + "_analysis.csv"
                output_path = os.path.join(settings.UPLOAD_DIR, output_name)

                combined_parts = [
                    pd.DataFrame([{"--- SECTION ---": "=== SUMMARY ==="}]),
                    summary_df,
                    pd.DataFrame([{"--- SECTION ---": "=== COLUMN ANALYSIS ==="}]),
                    col_df,
                    pd.DataFrame([{"--- SECTION ---": "=== DATA QUALITY ==="}]),
                    quality_df,
                ]
                if corr_df is not None:
                    combined_parts.append(pd.DataFrame([{"--- SECTION ---": "=== CORRELATIONS ==="}]))
                    combined_parts.append(corr_df.reset_index())
                if dist_df is not None:
                    combined_parts.append(pd.DataFrame([{"--- SECTION ---": "=== DISTRIBUTIONS ==="}]))
                    combined_parts.append(dist_df)

                combined = pd.concat(combined_parts, ignore_index=True)
                combined.to_csv(output_path, index=False)
                logger.info(f"Analysis CSV written: {output_path}")

            # ── Register output file in DB ──
            output_file_id = self._register_output_file(
                context, output_name, output_path
            )

            # ── Build response ──
            analysis_summary = {
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "numeric_columns": numeric_cols,
                "categorical_columns": cat_cols,
                "datetime_columns": dt_cols,
                "missing_values": int(df.isnull().sum().sum()),
                "missing_pct": round(df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100, 2) if len(df) > 0 and len(df.columns) > 0 else 0,
                "duplicate_rows": int(df.duplicated().sum()),
            }

            if numeric_cols:
                analysis_summary["numeric_highlights"] = {}
                for col in numeric_cols[:8]:
                    series = df[col].dropna()
                    if not series.empty:
                        analysis_summary["numeric_highlights"][col] = {
                            "min": round(float(series.min()), 4),
                            "max": round(float(series.max()), 4),
                            "mean": round(float(series.mean()), 4),
                            "median": round(float(series.median()), 4),
                        }

            if dt_cols:
                analysis_summary["datetime_highlights"] = {}
                for col in dt_cols[:3]:
                    series = df[col].dropna()
                    if not series.empty:
                        analysis_summary["datetime_highlights"][col] = {
                            "earliest": str(series.min()),
                            "latest": str(series.max()),
                        }

            return {
                "status": "completed",
                "message": f"Analysis complete. Output file: {output_name}",
                "output_file": {
                    "name": output_name,
                    "path": output_path,
                    "file_id": output_file_id,
                },
                "analysis": analysis_summary,
                "source_file": original_name,
                "encoding_used": encoding,
            }

        except Exception as e:
            logger.error(f"CSV export failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
            }

    def _register_output_file(self, context: Dict[str, Any], name: str, path: str):
        """Register the output file in the database using the shared async helper."""
        user_id = context.get("user_id")
        if not user_id:
            return None

        try:
            from ..core.database import fetch_val
            file_id = self._run_async(
                fetch_val(
                    "INSERT INTO files (user_id, file_name, file_path) VALUES ($1, $2, $3) RETURNING id",
                    user_id, name, path,
                ),
                context=context,
            )
            logger.info(f"Output file registered in DB: id={file_id}")
            return file_id
        except Exception as e:
            logger.warning(f"Could not register output file in DB: {e}")
            return None
