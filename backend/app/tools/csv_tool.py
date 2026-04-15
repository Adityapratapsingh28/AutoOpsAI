"""
AutoOps AI — CSV Tool.

Reads, analyzes, and processes CSV files using pandas.
Provides summary statistics, column info, and data insights.
Handles multiple encodings gracefully.
"""

import os
import logging
from typing import Any, Dict, List

from .base_tool import BaseTool

logger = logging.getLogger("autoops.tools.csv")

# Encodings to try in order
ENCODINGS = ["utf-8", "latin-1", "cp1252", "iso-8859-1", "utf-16"]

# Separators to try in order
SEPARATORS = [",", ";", "\t", "|"]


def read_csv_safe(file_path: str):
    """Read a CSV or Excel file robustly.

    Handles:
      - Excel files (.xlsx, .xls) via pd.read_excel()
      - Multiple encodings (utf-8, latin-1, cp1252, iso-8859-1, utf-16)
      - Multiple delimiters (comma, semicolon, tab, pipe)
      - Bad/inconsistent lines (skipped with warning instead of crash)
    """
    import pandas as pd

    # ── 1. Auto-detect Excel files by extension or magic bytes ──
    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".xlsx", ".xls", ".xlsm", ".xlsb"):
        try:
            df = pd.read_excel(file_path, engine="openpyxl" if ext != ".xls" else None)
            logger.info(f"Excel file loaded: {file_path} ({len(df)} rows, {len(df.columns)} cols)")
            return df, f"excel ({ext})"
        except Exception as e:
            logger.warning(f"Failed to read as Excel: {e}")

    # Check for Excel magic bytes (PK header = ZIP = xlsx) even if extension is .csv
    try:
        with open(file_path, "rb") as f:
            magic = f.read(4)
        if magic[:2] == b"PK":  # ZIP/XLSX file disguised as CSV
            try:
                df = pd.read_excel(file_path, engine="openpyxl")
                logger.info(f"File detected as Excel (PK header): {file_path}")
                return df, "excel (auto-detected)"
            except Exception:
                pass
    except Exception:
        pass

    # ── 2. Try CSV with multiple encodings + separators + bad line handling ──
    last_error = None
    for encoding in ENCODINGS:
        for sep in SEPARATORS:
            try:
                df = pd.read_csv(
                    file_path,
                    encoding=encoding,
                    sep=sep,
                    on_bad_lines="warn",
                    engine="python",
                )
                # Sanity check: if only 1 column was detected, the separator is probably wrong
                if len(df.columns) <= 1 and sep != SEPARATORS[-1]:
                    continue

                logger.info(
                    f"CSV loaded: encoding={encoding}, sep={repr(sep)}, "
                    f"{len(df)} rows, {len(df.columns)} cols"
                )
                return df, encoding
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                last_error = e
                continue

    raise ValueError(
        f"Could not read file with any encoding/separator combination. "
        f"Last error: {last_error}"
    )


class CSVTool(BaseTool):
    name = "csv_tool"
    description = "Reads and analyzes CSV files"

    def run(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a CSV file.

        input_data:
            - file_path: Path to the CSV file
            - query: Optional analysis query (e.g., "summarize", "top 10 rows")
        """
        import pandas as pd

        file_path = input_data.get("file_path", "")
        query = input_data.get("query", "summarize")

        if not file_path or not os.path.exists(file_path):
            return {
                "status": "failed",
                "error": f"CSV file not found: {file_path}",
            }

        try:
            df, encoding = read_csv_safe(file_path)
            logger.info(f"CSV loaded: {file_path} — {len(df)} rows, {len(df.columns)} columns")

            result = {
                "status": "completed",
                "file": os.path.basename(file_path),
                "rows": len(df),
                "columns": list(df.columns),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "encoding_used": encoding,
            }

            # Compute analysis
            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
            cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

            # Null analysis
            null_counts = df.isnull().sum().to_dict()
            null_pcts = {col: round(v / len(df) * 100, 1) for col, v in null_counts.items() if v > 0}

            result["null_counts"] = null_counts
            result["null_percentages"] = null_pcts

            # Numeric stats
            if numeric_cols:
                stats = df[numeric_cols].describe().to_dict()
                result["numeric_statistics"] = stats

                # Correlations (if 2+ numeric columns)
                if len(numeric_cols) >= 2:
                    corr = df[numeric_cols].corr().round(3).to_dict()
                    result["correlations"] = corr

            # Categorical stats
            if cat_cols:
                cat_stats = {}
                for col in cat_cols[:10]:  # Limit to 10 columns
                    vc = df[col].value_counts().head(10).to_dict()
                    cat_stats[col] = {
                        "unique_count": df[col].nunique(),
                        "top_values": vc,
                    }
                result["categorical_statistics"] = cat_stats

            # Sample rows
            result["sample_rows"] = df.head(5).to_dict(orient="records")

            return result

        except Exception as e:
            logger.error(f"CSV analysis failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
            }
