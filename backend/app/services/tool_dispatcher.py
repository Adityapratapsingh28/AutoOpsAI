"""
AutoOps AI — Tool Dispatcher.

Executes tools by name. Tool assignments come from the LLM (via the "tool"
field in agent configs), not from keyword guessing. The orchestrator_service
reads the LLM-assigned tool and calls execute_tool() directly.
Each tool is independent and exposes: run(input_data, context)
"""


import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("autoops.tool_dispatcher")


# ── Tool Registry (lazy imports to avoid startup overhead) ──

def _get_tool(tool_name: str):
    """Lazy-load and return a tool instance by name."""
    if tool_name == "csv_tool":
        from ..tools.csv_tool import CSVTool
        return CSVTool()
    elif tool_name == "csv_export_tool":
        from ..tools.csv_export_tool import CSVExportTool
        return CSVExportTool()
    elif tool_name == "report_tool":
        from ..tools.report_tool import ReportTool
        return ReportTool()
    elif tool_name == "email_tool":
        from ..tools.email_tool import EmailTool
        return EmailTool()
    elif tool_name == "slack_tool":
        from ..tools.slack_tool import SlackTool
        return SlackTool()
    elif tool_name == "zoom_tool":
        from ..tools.zoom_tool import ZoomTool
        return ZoomTool()
    elif tool_name == "calendar_tool":
        from ..tools.calendar_tool import CalendarTool
        return CalendarTool()
    elif tool_name == "email_reader_tool":
        from ..tools.email_reader_tool import EmailReaderTool
        return EmailReaderTool()
    elif tool_name == "sql_tool":
        from ..tools.sql_tool import SQLTool
        return SQLTool()
    elif tool_name == "data_summarizer_tool":
        from ..tools.data_summarizer_tool import DataSummarizerTool
        return DataSummarizerTool()
    else:
        return None



def execute_tool(tool_name: str, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Execute a tool by name.

    Args:
        tool_name: The registered tool name (e.g., 'csv_tool')
        input_data: Input data for the tool
        context: Optional execution context

    Returns:
        Tool execution result as a dictionary
    """
    tool = _get_tool(tool_name)

    if not tool:
        logger.warning(f"No tool found for: {tool_name}")
        return {
            "status": "skipped",
            "message": f"Tool '{tool_name}' not found in registry",
        }

    try:
        logger.info(f"Executing tool: {tool_name}")
        result = tool.run(input_data, context or {})
        logger.info(f"Tool {tool_name} completed successfully")
        return result
    except Exception as e:
        logger.error(f"Tool {tool_name} failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "tool": tool_name,
        }
