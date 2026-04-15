"""
AutoOps AI — Slack Tool.

Sends messages to Slack channels using the Bot Token API.
"""

import logging
from typing import Any, Dict

import httpx

from .base_tool import BaseTool

logger = logging.getLogger("autoops.tools.slack")


class SlackTool(BaseTool):
    name = "slack_tool"
    description = "Sends messages to Slack channels"

    def run(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a Slack message.

        input_data:
            - channel: Slack channel ID or name (e.g., '#general')
            - text: Message text
        """
        from ..core.config import settings

        channel = input_data.get("channel", "#general")
        text = input_data.get("text", "")

        if not text:
            return {"status": "failed", "error": "No message text provided"}

        if not settings.SLACK_BOT_TOKEN:
            logger.warning("Slack bot token not configured — simulating message")
            return {
                "status": "completed",
                "message": f"Slack message simulated. Channel: {channel}, Text: {text[:100]}...",
                "simulated": True,
            }

        try:
            response = httpx.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "channel": channel,
                    "text": text,
                },
                timeout=10,
            )

            data = response.json()

            if data.get("ok"):
                logger.info(f"Slack message sent to {channel}")
                return {
                    "status": "completed",
                    "message": f"Message sent to {channel}",
                    "channel": channel,
                    "ts": data.get("ts"),
                }
            else:
                error = data.get("error", "Unknown Slack API error")
                logger.error(f"Slack API error: {error}")
                return {"status": "failed", "error": error}

        except Exception as e:
            logger.error(f"Slack tool failed: {e}")
            return {"status": "failed", "error": str(e)}
