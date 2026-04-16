"""
AutoOps AI — Zoom Tool.

Creates Zoom meetings using Server-to-Server OAuth.
"""

import logging
from typing import Any, Dict
from datetime import datetime, timedelta
import time

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
        if response.status_code != 200:
            logger.error(f"Zoom OAuth failed: {response.status_code} - {response.text}")
        response.raise_for_status()
        token = response.json()["access_token"]
        logger.debug("Zoom OAuth token retrieved successfully.")
        return token

    def run(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a Zoom meeting.

        input_data:
            - topic: Meeting topic
            - duration: Duration in minutes (default: 30)
            - start_time: ISO datetime string (default: +1 hour from now)
        """
        from ..core.config import settings
        import json

        topic = "AutoOps AI Meeting"
        duration = 30
        start_time = (datetime.utcnow() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        input_text = input_data.get("input_text", "")

        # Use LLM to extract requested time/topic
        if input_text and settings.GROQ_API_KEY:
            try:
                from datetime import timezone
                ist = timezone(timedelta(hours=5, minutes=30))
                now_ist = datetime.now(ist).strftime("%Y-%m-%d %H:%M")
                sys_prompt = (
                    f"The current local time is {now_ist}. "
                    "Extract meeting topic/agenda. Extract duration in minutes. "
                    "Calculate the requested start_time in local time (format: YYYY-MM-DDTHH:MM:SS) "
                    "Return strictly JSON with keys: 'topic', 'duration', 'start_time'. If vague, return nulls."
                )
                
                response = httpx.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                    json={
                        "model": settings.LLM_MODEL,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": sys_prompt},
                            {"role": "user", "content": input_text}
                        ],
                        "temperature": 0.1
                    },
                    timeout=8
                )
                if response.status_code == 200:
                    parsed = json.loads(response.json()["choices"][0]["message"]["content"])
                    if parsed.get("topic"): topic = parsed["topic"]
                    if parsed.get("duration"): duration = int(parsed["duration"])
                    if parsed.get("start_time"):
                        local_time_str = parsed["start_time"].replace('Z', '')
                        # Convert local time to UTC explicitly in python
                        from datetime import datetime as dt
                        try:
                            local_dt = dt.strptime(local_time_str, "%Y-%m-%dT%H:%M:%S")
                            local_dt = local_dt.replace(tzinfo=ist)
                            start_time = local_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                        except Exception as dt_e:
                            logger.warning(f"Failed parsing local time {local_time_str}: {dt_e}")
            except Exception as e:
                logger.warning(f"Zoom LLM parsing error: {e}")

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

        for attempt in range(3):
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

                if response.status_code in [429, 500, 502, 503, 504]:
                    logger.warning(f"Zoom transient error {response.status_code}, retrying...")
                    time.sleep(2 ** attempt)
                    continue

                response.raise_for_status()
                data = response.json()
                logger.info(f"Zoom meeting created successfully: {data.get('join_url')}")

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
                logger.error(f"Zoom tool attempt {attempt+1} failed: {e}")
                if attempt == 2:
                    logger.error("All Zoom retries exhausted — returning simulated fallback")
                    return {
                        "status": "completed",
                        "message": "Zoom API unavailable — simulated fallback used.",
                        "simulated": True,
                        "zoom_error": str(e),
                        "meeting": {
                            "topic": topic,
                            "duration": duration,
                            "start_time": start_time,
                            "join_url": "https://zoom.us/j/simulated",
                        },
                    }
                time.sleep(1)
