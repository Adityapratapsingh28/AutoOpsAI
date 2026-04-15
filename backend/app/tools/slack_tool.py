"""
AutoOps AI — Slack Integration Tool.

Handles posting to specific Slack channels using precise Channel IDs.
Ensures non-blocking fallback and retry logic.
"""

import logging
from typing import Any, Dict, List, Optional
import httpx

from .base_tool import BaseTool
from ..core.config import settings

logger = logging.getLogger("autoops.tools.slack")

CHANNEL_MAP = {
    "alerts": "C0ASB25PY2X",
    "all-hackstorm": "C0ASM0Q7PGC",
    "engineering": "C0ATBME3AP2",
    "general": "C0ASHD9EF8A",
    "management": "C0ASE1MMSJ1",
    "new-channel": "C0ATBLWD7NC",
    "sales-team": "C0ASFBEFQ22",
    "social": "C0ASW9QCETB",
    "meetings": "C0AT3RNTY3X",
    "data-processing": "C0ATL57QVDX"
}

class SlackTool(BaseTool):
    name = "slack_tool"
    description = "Communicates with teams via Slack using specific channels."

    def __init__(self):
        self.base_url = "https://slack.com/api"
        self.headers = {
            "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
            "Content-Type": "application/json; charset=utf-8"
        }

    def _resolve_channel_id(self, channel_request: str) -> str:
        """Resolve a requested channel string to the exact Slack Channel ID."""
        clean = channel_request.lower().replace("#", "").strip()
        return CHANNEL_MAP.get(clean, CHANNEL_MAP["all-hackstorm"])  # Default fallback if unknown

    def _safe_slack_send(self, payload: Dict[str, Any]) -> bool:
        """Sends a payload to Slack with a 1-time retry. Non-blocking failure."""
        token = settings.SLACK_BOT_TOKEN
        if not token:
            logger.warning("SLACK_BOT_TOKEN not found in .env, skipping Slack send.")
            return False
            
        def _attempt():
            try:
                resp = httpx.post(f"{self.base_url}/chat.postMessage", headers=self.headers, json=payload, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                if data.get("ok"):
                    logger.info(f"Slack success: {data.get('ts')}")
                    return True
                else:
                    logger.error(f"Slack API error: {data.get('error')}")
                    return False
            except Exception as e:
                logger.error(f"Slack network/execution error: {e}")
                return False

        success = _attempt()
        if not success:
            logger.warning("Retrying Slack...")
            success = _attempt()
            
        if not success:
            logger.warning("Slack failed, continuing pipeline...")
            
        return success

    def run(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes Slack routing dynamically based on orchestrator intent.
        Never breaks existing logic if it fails.
        """
        action = input_data.get("action", "post_message")
        message = input_data.get("message", "AutoOps Notification")
        prev_results = input_data.get("previous_tool_results", {})
        
        # Determine the target channel provided by the LLM
        req_channel = input_data.get("channel_name", "all-hackstorm")
        
        # Support dynamic override
        if action == "post_meeting" or "meeting" in str(prev_results).lower():
            # Broadcast meetings and summaries to all-hackstorm per requirements
            self._broadcast_meeting(prev_results, CHANNEL_MAP["all-hackstorm"])
        elif action == "post_alert" or "analysis" in str(prev_results).lower():
            # Broadcast the anomaly alert and summary explicitly to alerts channel
            self._send_data_alert(prev_results, CHANNEL_MAP["alerts"])
        else:
            # Fallback direct channel message
            channel_id = self._resolve_channel_id(req_channel)
            self._safe_slack_send({"channel": channel_id, "text": message})

        # To keep pipeline moving reliably
        return {
            "status": "completed",
            "message": "Slack process completed (or bypassed safely).",
        }

    def _broadcast_meeting(self, prev_results: Dict[str, Any], channel_id: str) -> None:
        """Sends meeting link."""
        mtg = None
        for agent_name, result in prev_results.items():
            if isinstance(result, dict) and result.get("meeting"):
                mtg = result["meeting"]
                break

        if mtg:
            join_url = mtg.get("join_url", "No Link")
            topic = mtg.get("topic", "Meeting")
            msg = f"*🚀 Meeting Created: {topic}*\n🔗 Link: {join_url}"
            self._safe_slack_send({"channel": channel_id, "text": msg})
        else:
            self._safe_slack_send({"channel": channel_id, "text": "📅 Meeting Created\n🔗 (Check dashboard for link)"})

    def _send_data_alert(self, prev_results: Dict[str, Any], channel_id: str) -> None:
        """Sends data alerts and/or Summary generated."""
        summary = ""
        for agent, res in prev_results.items():
            if isinstance(res, dict) and res.get("analysis"):
                analysis = res["analysis"]
                missing = analysis.get("missing_values", 0)
                if int(missing) > 0:
                    summary += f"🚨 *Alert*: Found {missing} missing rows in data.\n"
                summary += "🧠 *Summary*:\nData processing pipeline completed."

        if summary:
            self._safe_slack_send({"channel": channel_id, "text": summary})
