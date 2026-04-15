"""
AutoOps AI — Calendar Tool.

Queries the internal meetings database for scheduling information.
Uses BaseTool._run_async() for safe async-to-sync bridging.
"""

import logging
import uuid
from typing import Any, Dict
from datetime import datetime, timedelta

from .base_tool import BaseTool

logger = logging.getLogger("autoops.tools.calendar")


class CalendarTool(BaseTool):
    name = "calendar_tool"
    description = "Queries internal meeting calendar from the database"

    def run(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query calendar/meetings.

        input_data:
            - user_id: User ID to fetch meetings for
            - action: 'list' | 'upcoming' | 'search' | 'create'
            - query: Search term for 'search' action
        """
        from ..core.database import fetch_all, fetch_val, execute

        user_id = input_data.get("user_id") or context.get("user_id")
        action = input_data.get("action", "list")

        if not user_id:
            return {"status": "failed", "error": "No user_id provided"}

        try:
            if action == "upcoming":
                rows = self._run_async(fetch_all(
                    "SELECT id, title, time, meeting_link, created_at FROM meetings WHERE user_id = $1 ORDER BY created_at DESC LIMIT 10",
                    user_id,
                ), context)
            elif action == "search":
                query = input_data.get("query", "")
                rows = self._run_async(fetch_all(
                    "SELECT id, title, time, meeting_link FROM meetings WHERE user_id = $1 AND title ILIKE $2",
                    user_id, f"%{query}%",
                ), context)
            elif action == "create" or "meeting" in input_data.get("llm_summary", "").lower() or "schedule" in input_data.get("input_text", "").lower():
                title = input_data.get("title", "AutoOps Generated Meeting")
                time_str = input_data.get("time", (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z")
                meeting_link = f"https://meet.google.com/autoops-{uuid.uuid4().hex[:8]}"

                meeting_id = self._run_async(fetch_val(
                    """
                    INSERT INTO meetings (user_id, title, time, meeting_link)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                    """,
                    user_id, title, time_str, meeting_link
                ), context)

                return {
                    "status": "completed",
                    "action": "create",
                    "meeting_id": meeting_id,
                    "title": title,
                    "time": time_str,
                    "meeting_link": meeting_link,
                }
            else:
                rows = self._run_async(fetch_all(
                    "SELECT id, title, time, meeting_link, created_at FROM meetings WHERE user_id = $1 ORDER BY created_at DESC",
                    user_id,
                ), context)

            meetings = [
                {
                    "id": r["id"],
                    "title": r["title"],
                    "time": r["time"],
                    "meeting_link": r["meeting_link"],
                }
                for r in rows
            ]

            return {
                "status": "completed",
                "meetings": meetings,
                "count": len(meetings),
            }

        except Exception as e:
            logger.error(f"Calendar tool failed: {e}")
            return {"status": "failed", "error": str(e)}
