"""
AutoOps AI — Zoom Tool.

Creates Zoom meetings using Server-to-Server OAuth.
"""

import logging
from typing import Any, Dict
from datetime import datetime, timedelta

import httpx

from .base_tool import BaseTool

logger = logging.getLogger("autoops.tools.zoom")


class ZoomTool(BaseTool):
    name = "zoom_tool"
    description = "Creates Zoom meetings"

    def _get_access_token(self, account_id: str, client_id: str, client_secret: str) -> str:
        """Get Zoom Server-to-Server OAuth access token."""
        response = httpx.post(
            f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={account_id}",
            auth=(client_id, client_secret),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def run(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a Zoom meeting.

        input_data:
            - topic: Meeting topic
            - duration: Duration in minutes (default: 30)
            - start_time: ISO datetime string (default: +1 hour from now)
        """
        from ..core.config import settings

        topic = input_data.get("topic", "AutoOps AI Meeting")
        duration = input_data.get("duration", 30)
        start_time = input_data.get(
            "start_time",
            (datetime.utcnow() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

        if not all([settings.ZOOM_ACCOUNT_ID, settings.ZOOM_CLIENT_ID, settings.ZOOM_CLIENT_SECRET]):
            logger.warning("Zoom credentials not configured — simulating meeting creation")
            return {
                "status": "completed",
                "message": f"Zoom meeting simulated. Topic: {topic}",
                "simulated": True,
                "meeting": {
                    "topic": topic,
                    "duration": duration,
                    "start_time": start_time,
                    "join_url": "https://zoom.us/j/simulated",
                },
            }

        try:
            access_token = self._get_access_token(
                settings.ZOOM_ACCOUNT_ID,
                settings.ZOOM_CLIENT_ID,
                settings.ZOOM_CLIENT_SECRET,
            )

            response = httpx.post(
                "https://api.zoom.us/v2/users/me/meetings",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "topic": topic,
                    "type": 2,
                    "start_time": start_time,
                    "duration": duration,
                    "settings": {
                        "join_before_host": True,
                        "mute_upon_entry": True,
                    },
                },
                timeout=15,
            )

            data = response.json()
            logger.info(f"Zoom meeting created: {data.get('join_url')}")

            return {
                "status": "completed",
                "message": f"Zoom meeting created: {topic}",
                "meeting": {
                    "id": data.get("id"),
                    "topic": data.get("topic"),
                    "join_url": data.get("join_url"),
                    "start_time": data.get("start_time"),
                    "duration": data.get("duration"),
                    "password": data.get("password"),
                },
            }

        except Exception as e:
            logger.error(f"Zoom tool failed: {e}")
            return {"status": "failed", "error": str(e)}
