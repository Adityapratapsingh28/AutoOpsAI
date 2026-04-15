"""
AutoOps AI — SQL Query Tool.

Executes read-only SQL queries against the application database.
Uses BaseTool._run_async() for safe async-to-sync bridging.
"""

import logging
from typing import Any, Dict

from .base_tool import BaseTool

logger = logging.getLogger("autoops.tools.sql")


class SQLTool(BaseTool):
    name = "sql_tool"
    description = "Executes read-only SQL queries"

    def run(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a SQL query (read-only).

        input_data:
            - query: SQL SELECT statement
        """
        from ..core.database import fetch_all

        query = input_data.get("query", "")

        if not query:
            return {"status": "failed", "error": "No SQL query provided"}

        # Safety: only allow SELECT statements
        normalized = query.strip().upper()
        if not normalized.startswith("SELECT"):
            return {
                "status": "failed",
                "error": "Only SELECT queries are allowed for security",
            }

        # Block dangerous keywords
        dangerous = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE", "CREATE"]
        for kw in dangerous:
            if kw in normalized:
                return {
                    "status": "failed",
                    "error": f"Query contains forbidden keyword: {kw}",
                }

        try:
            rows = self._run_async(fetch_all(query), context)
            results = [dict(r) for r in rows]

            return {
                "status": "completed",
                "rows": len(results),
                "data": results[:100],  # Cap at 100 rows
            }

        except Exception as e:
            logger.error(f"SQL tool failed: {e}")
            return {"status": "failed", "error": str(e)}
