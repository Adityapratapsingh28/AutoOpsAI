"""
AutoOps AI — Email Reader Tool.

Reads emails via IMAP for processing email-based workflows.
"""

import logging
import imaplib
import email
from email.header import decode_header
from typing import Any, Dict, List

from .base_tool import BaseTool

logger = logging.getLogger("autoops.tools.email_reader")


class EmailReaderTool(BaseTool):
    name = "email_reader_tool"
    description = "Reads emails from an inbox via IMAP"

    def run(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Read emails from inbox.

        input_data:
            - count: Number of recent emails to fetch (default: 5)
            - folder: IMAP folder (default: 'INBOX')
        """
        from ..core.config import settings

        count = input_data.get("count", 5)
        folder = input_data.get("folder", "INBOX")

        imap_host = input_data.get("imap_host", "imap.gmail.com")
        imap_user = input_data.get("imap_user", settings.SMTP_USER)
        imap_pass = input_data.get("imap_pass", settings.SMTP_PASS)

        if not imap_user or not imap_pass:
            logger.warning("IMAP credentials not configured — simulating email read")
            return {
                "status": "completed",
                "message": "Email read simulated (IMAP not configured)",
                "simulated": True,
                "emails": [
                    {"from": "user@example.com", "subject": "Sample Email", "date": "2024-01-01"},
                ],
            }

        try:
            mail = imaplib.IMAP4_SSL(imap_host)
            mail.login(imap_user, imap_pass)
            mail.select(folder)

            _, message_ids = mail.search(None, "ALL")
            ids = message_ids[0].split()
            latest_ids = ids[-count:] if len(ids) >= count else ids

            emails: List[Dict[str, Any]] = []

            for mid in reversed(latest_ids):
                _, msg_data = mail.fetch(mid, "(RFC822)")
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                subject_raw = decode_header(msg["Subject"])[0]
                subject = subject_raw[0].decode(subject_raw[1] or "utf-8") if isinstance(subject_raw[0], bytes) else str(subject_raw[0])

                emails.append({
                    "from": msg["From"],
                    "subject": subject,
                    "date": msg["Date"],
                })

            mail.logout()

            return {
                "status": "completed",
                "emails": emails,
                "count": len(emails),
            }

        except Exception as e:
            logger.error(f"Email reader failed: {e}")
            return {"status": "failed", "error": str(e)}
