"""
AutoOps AI — Report Tool.

Takes agent results and analysis data from previous tools to generate
a structured human-readable report as the final workflow output.
Handles partial failures gracefully — generates the best report possible
even when upstream tools produced errors or incomplete data.
"""

import logging
from typing import Any, Dict, List
from datetime import datetime

from .base_tool import BaseTool

logger = logging.getLogger("autoops.tools.report")


class ReportTool(BaseTool):
    name = "report_tool"
    description = "Generates structured reports from workflow results"

    def run(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a structured report from workflow execution data.

        input_data:
            - llm_summary: The Report Generator agent's LLM summary
            - input_text: User's original prompt
            - previous_tool_results: Dict of results from earlier tools
              (injected by orchestrator_service)

        Returns:
            - report: Formatted report text with actual analysis data
        """
        llm_summary = input_data.get("llm_summary", "")
        input_text = input_data.get("input_text", "")
        workflow_id = context.get("workflow_id", "unknown")
        prev_results = input_data.get("previous_tool_results", {})

        try:
            lines = []

            # ── Header ──
            lines.append("=" * 60)
            lines.append("  AUTOOPS AI — WORKFLOW ANALYSIS REPORT")
            lines.append("=" * 60)
            lines.append("")
            lines.append(f"  Workflow ID : {workflow_id}")
            lines.append(f"  Generated   : {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            lines.append(f"  User Request: {input_text}")

            # ── Collect data from previous tools ──
            csv_analysis = None
            output_file_info = None
            llm_file_summary = None
            file_info = None
            tool_errors = []
            all_tool_summaries = []

            for agent_name, tool_result in prev_results.items():
                if not isinstance(tool_result, dict):
                    continue

                # Track errors from upstream tools
                if tool_result.get("status") == "failed":
                    tool_errors.append({
                        "agent": agent_name,
                        "error": tool_result.get("error", "Unknown error"),
                    })
                    continue

                # Extract CSV analysis data (from csv_export_tool)
                if "analysis" in tool_result:
                    csv_analysis = tool_result["analysis"]
                if "output_file" in tool_result:
                    output_file_info = tool_result["output_file"]
                if "source_file" in tool_result:
                    lines.append(f"  Source File : {tool_result['source_file']}")
                if "encoding_used" in tool_result:
                    lines.append(f"  Encoding    : {tool_result['encoding_used']}")

                # Extract LLM summary (from data_summarizer_tool)
                if "summary" in tool_result and isinstance(tool_result["summary"], str):
                    llm_file_summary = tool_result["summary"]
                if "file_info" in tool_result and isinstance(tool_result["file_info"], dict):
                    file_info = tool_result["file_info"]

                # Collect tool summaries for the report
                if tool_result.get("message"):
                    all_tool_summaries.append(f"  [{agent_name}] {tool_result['message']}")

                # Handle meeting results
                if "meeting_link" in tool_result or "meetings" in tool_result:
                    all_tool_summaries.append(f"  [{agent_name}] Meeting data available")

                # Handle email results
                if tool_result.get("to"):
                    all_tool_summaries.append(f"  [{agent_name}] Email sent to {tool_result['to']}")

            # ── Upstream Errors Section ──
            if tool_errors:
                lines.append("")
                lines.append("-" * 60)
                lines.append("  ⚠ UPSTREAM TOOL ERRORS")
                lines.append("-" * 60)
                for err in tool_errors:
                    lines.append(f"  Agent: {err['agent']}")
                    lines.append(f"  Error: {err['error'][:200]}")
                    lines.append("")

            # ── LLM File Summary Section (from data_summarizer_tool) ──
            if llm_file_summary:
                lines.append("")
                lines.append("-" * 60)
                lines.append("  FILE SUMMARY (AI-Generated)")
                lines.append("-" * 60)
                if file_info:
                    lines.append("")
                    lines.append(f"  File Name : {file_info.get('name', 'N/A')}")
                    lines.append(f"  Format    : {file_info.get('format', 'N/A')}")
                    if file_info.get('rows') is not None:
                        lines.append(f"  Rows      : {file_info['rows']}")
                    if file_info.get('cols') is not None:
                        lines.append(f"  Columns   : {file_info['cols']}")
                lines.append("")
                # Include the full LLM-generated summary
                for summary_line in llm_file_summary.split('\n'):
                    lines.append(f"  {summary_line}")

            # ── Data Analysis Section (from csv_export_tool) ──
            if csv_analysis:
                lines.append("")
                lines.append("-" * 60)
                lines.append("  DATA ANALYSIS SUMMARY")
                lines.append("-" * 60)
                lines.append("")
                lines.append(f"  Total Rows       : {csv_analysis.get('total_rows', 'N/A'):,}")
                lines.append(f"  Total Columns    : {csv_analysis.get('total_columns', 'N/A')}")
                lines.append(f"  Missing Values   : {csv_analysis.get('missing_values', 'N/A'):,}")

                missing_pct = csv_analysis.get("missing_pct")
                if missing_pct is not None:
                    lines.append(f"  Missing Value %  : {missing_pct}%")

                lines.append(f"  Duplicate Rows   : {csv_analysis.get('duplicate_rows', 'N/A'):,}")

                num_cols = csv_analysis.get("numeric_columns", [])
                cat_cols = csv_analysis.get("categorical_columns", [])
                dt_cols = csv_analysis.get("datetime_columns", [])

                lines.append(f"  Numeric Columns  : {len(num_cols)} — {', '.join(num_cols[:6])}")
                lines.append(f"  Categorical Cols : {len(cat_cols)} — {', '.join(cat_cols[:6])}")
                if dt_cols:
                    lines.append(f"  Datetime Cols    : {len(dt_cols)} — {', '.join(dt_cols[:3])}")

                # Numeric highlights table
                highlights = csv_analysis.get("numeric_highlights", {})
                if highlights:
                    lines.append("")
                    lines.append("  NUMERIC COLUMN HIGHLIGHTS:")
                    lines.append("  " + "-" * 56)
                    lines.append(f"  {'Column':<20} {'Min':>10} {'Max':>10} {'Mean':>10}")
                    lines.append("  " + "-" * 56)
                    for col, stats in highlights.items():
                        min_v = self._fmt_num(stats.get("min"))
                        max_v = self._fmt_num(stats.get("max"))
                        mean_v = self._fmt_num(stats.get("mean"))
                        lines.append(f"  {col:<20} {min_v:>10} {max_v:>10} {mean_v:>10}")

                # Datetime highlights
                dt_highlights = csv_analysis.get("datetime_highlights", {})
                if dt_highlights:
                    lines.append("")
                    lines.append("  DATETIME COLUMN HIGHLIGHTS:")
                    lines.append("  " + "-" * 56)
                    for col, stats in dt_highlights.items():
                        lines.append(f"  {col}: {stats.get('earliest', '?')} → {stats.get('latest', '?')}")

            # ── No analysis at all ──
            if not csv_analysis and not llm_file_summary:
                lines.append("")
                lines.append("-" * 60)
                lines.append("  DATA ANALYSIS SUMMARY")
                lines.append("-" * 60)
                lines.append("")
                lines.append("  No analysis data available.")
                if tool_errors:
                    lines.append("  (Upstream analysis tool encountered errors — see above)")
                else:
                    lines.append("  (No data file was attached or analysis tool did not run)")

            # ── Output File Section ──
            if output_file_info:
                lines.append("")
                lines.append("-" * 60)
                lines.append("  OUTPUT FILE")
                lines.append("-" * 60)
                lines.append("")
                lines.append(f"  File Name : {output_file_info.get('name', 'N/A')}")
                lines.append(f"  File Path : {output_file_info.get('path', 'N/A')}")
                if output_file_info.get("file_id"):
                    lines.append(f"  File ID   : {output_file_info['file_id']}")

            # ── Tool Execution Summary ──
            if all_tool_summaries:
                lines.append("")
                lines.append("-" * 60)
                lines.append("  TOOL EXECUTION LOG")
                lines.append("-" * 60)
                lines.append("")
                for summary in all_tool_summaries:
                    lines.append(summary)

            # ── Agent Reasoning Summary ──
            lines.append("")
            lines.append("-" * 60)
            lines.append("  AGENT REASONING SUMMARY")
            lines.append("-" * 60)
            lines.append("")
            lines.append(f"  {llm_summary if llm_summary else 'No summary available.'}")

            # ── Footer ──
            lines.append("")
            lines.append("-" * 60)
            if tool_errors:
                lines.append("  STATUS: COMPLETED WITH WARNINGS ⚠️")
            else:
                lines.append("  STATUS: COMPLETED ✅")
            lines.append("-" * 60)

            report_text = "\n".join(lines)

            return {
                "status": "completed",
                "message": "Report generated successfully",
                "report": report_text,
                "has_csv_analysis": csv_analysis is not None,
                "has_output_file": output_file_info is not None,
                "upstream_errors": len(tool_errors),
            }

        except Exception as e:
            logger.error(f"Report generation failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
            }

    @staticmethod
    def _fmt_num(value) -> str:
        """Format a number for display — handles None, int, float."""
        if value is None:
            return "N/A"
        if isinstance(value, float):
            if abs(value) >= 1_000_000:
                return f"{value:,.0f}"
            elif abs(value) >= 100:
                return f"{value:,.2f}"
            else:
                return f"{value:.4f}"
        return str(value)
