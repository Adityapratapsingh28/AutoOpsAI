"""
AutoOps AI — Email Tool.

Sends emails via SMTP with smart recipient resolution and report file attachment.
Supports:
  - Direct email addresses
  - Team-based lookup ("send to engineering team") → queries teams + team_members
  - Person name lookup ("send to John", "send to Priyanshu") → queries team_members + users
  - Auto-attaches generated report files from previous tool outputs
  - NLP-based intent extraction for natural language prompts

Database Schema Used:
  - teams (id, name, slug, description, is_active)
  - team_members (user_id, team_id, team_name, work_email, phone_number, designation, role, is_active)
  - users (id, full_name, email, is_active)
"""

import os
import re
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Any, Dict, List, Optional, Tuple

from .base_tool import BaseTool

logger = logging.getLogger("autoops.tools.email")


class EmailTool(BaseTool):
    name = "email_tool"
    description = "Sends emails via SMTP with team/person resolution from database and file attachment"

    def run(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send an email with smart recipient resolution and optional file attachment.

        input_data:
            - llm_summary: The agent's LLM reasoning (contains recipient hints)
            - input_text: User's original prompt (contains recipient intent)
            - previous_tool_results: Results from earlier agents (report/summary to send)
            - to: (optional) Direct email address override
            - subject: (optional) Email subject
            - body: (optional) Email body override
        """
        from ..core.config import settings

        llm_summary = input_data.get("llm_summary", "")
        input_text = input_data.get("input_text", "")
        prev_results = input_data.get("previous_tool_results", {})

        # ── 1. Resolve recipients ──
        recipients, resolution_log = self._resolve_recipients(
            input_text=input_text,
            llm_summary=llm_summary,
            direct_to=input_data.get("to", ""),
            context=context,
        )

        if not recipients:
            return {
                "status": "failed",
                "error": "Could not resolve any email recipients. "
                         "Specify a team name, person name, or email address in your prompt.",
                "resolution_log": resolution_log,
            }

        # ── 2. Build email body from previous tool results ──
        subject = input_data.get("subject", "")
        body = input_data.get("body", "")

        if not body:
            body = self._build_email_body(prev_results, llm_summary, input_text)

        if not subject:
            subject = self._generate_subject(input_text, prev_results)

        # ── 3. Discover report file to attach ──
        attachment_path, attachment_name = self._find_report_file(prev_results, context)
        if attachment_path:
            resolution_log.append(f"Report file found for attachment: {attachment_name}")
        else:
            resolution_log.append("No report file found — sending email with body text only")

        # ── 4. Build HTML body ──
        html_body = self._build_html_body(body, subject)

        # ── 5. Send emails ──
        if not settings.SMTP_USER or not settings.SMTP_PASS:
            logger.warning("SMTP credentials not configured — simulating email send")
            return {
                "status": "completed",
                "message": f"Email simulated (SMTP not configured). "
                           f"To: {', '.join(recipients)}, Subject: {subject}",
                "simulated": True,
                "recipients": recipients,
                "recipient_count": len(recipients),
                "resolution_log": resolution_log,
                "has_attachment": attachment_path is not None,
                "attachment_name": attachment_name,
                "body_snippet": body[:200] + "..." if len(body) > 200 else body,
            }

        sent_to = []
        errors = []

        for recipient in recipients:
            try:
                self._send_smtp(
                    smtp_host=settings.SMTP_HOST,
                    smtp_port=settings.SMTP_PORT,
                    smtp_user=settings.SMTP_USER,
                    smtp_pass=settings.SMTP_PASS,
                    to_email=recipient,
                    subject=subject,
                    plain_body=body,
                    html_body=html_body,
                    attachment_path=attachment_path,
                    attachment_name=attachment_name,
                )
                sent_to.append(recipient)
                logger.info(f"Email sent to: {recipient}")
            except Exception as e:
                logger.error(f"Failed to send to {recipient}: {e}")
                errors.append({"email": recipient, "error": str(e)})

        if sent_to:
            return {
                "status": "completed",
                "message": f"Email sent successfully to {len(sent_to)} recipient(s): {', '.join(sent_to)}",
                "to": ", ".join(sent_to),
                "recipients": sent_to,
                "recipient_count": len(sent_to),
                "subject": subject,
                "has_attachment": attachment_path is not None,
                "attachment_name": attachment_name,
                "resolution_log": resolution_log,
                "errors": errors if errors else None,
            }
        else:
            return {
                "status": "failed",
                "error": f"Failed to send to all {len(recipients)} recipients",
                "errors": errors,
                "resolution_log": resolution_log,
            }

    # ─────────────────────────────────────────────
    # RECIPIENT RESOLUTION (NLP + DB Lookup)
    # ─────────────────────────────────────────────

    def _resolve_recipients(
        self,
        input_text: str,
        llm_summary: str,
        direct_to: str,
        context: Dict[str, Any],
    ) -> Tuple[List[str], List[str]]:
        """
        Resolve email recipients using NLP parsing + database lookups.

        Resolution order:
          1. Direct email address in input
          2. Team name → lookup teams + team_members table
          3. Person name → lookup team_members + users table
          4. "all members" / "everyone" → all active team members
          5. Fallback to user's own email

        Returns:
            (list of email addresses, resolution log messages)
        """
        log = []
        recipients = set()

        # Use lowered text for keyword matching
        combined_lower = f"{input_text} {llm_summary}".lower()
        # Keep original case for name extraction
        combined_original = f"{input_text} {llm_summary}"

        # ── Step 1: Check for direct email addresses ──
        if direct_to and "@" in direct_to:
            for email in re.split(r"[,;\s]+", direct_to):
                email = email.strip()
                if "@" in email:
                    recipients.add(email)
                    log.append(f"Direct email provided: {email}")

        # Extract emails from user prompt
        email_pattern = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
        found_emails = re.findall(email_pattern, input_text)
        for email in found_emails:
            recipients.add(email.lower())
            log.append(f"Email extracted from prompt: {email}")

        if recipients:
            return list(recipients), log

        # ── Step 2: Check for team-based sending ──
        team_name = self._extract_team_name(combined_lower)
        if team_name:
            log.append(f"Team name detected: '{team_name}'")
            team_emails = self._lookup_team_emails(team_name, context)
            if team_emails:
                recipients.update(team_emails)
                log.append(f"Found {len(team_emails)} member(s) in team '{team_name}': {', '.join(team_emails)}")
            else:
                log.append(f"No members found for team '{team_name}'")

        # ── Step 3: Check for person name ──
        if not recipients:
            person_names = self._extract_person_names(combined_original)
            if person_names:
                for name in person_names:
                    log.append(f"Person name detected: '{name}'")
                    person_email = self._lookup_person_email(name, context)
                    if person_email:
                        recipients.add(person_email)
                        log.append(f"Resolved '{name}' → {person_email}")
                    else:
                        log.append(f"Could not find email for person '{name}'")

        # ── Step 4: Check for "all members" / "everyone" ──
        if not recipients:
            all_keywords = [
                "all members", "everyone", "all employees", "all team members",
                "all teams", "entire team", "whole team", "every member",
                "all the members", "each member", "complete team",
            ]
            if any(kw in combined_lower for kw in all_keywords):
                log.append("Detected 'all members' intent — fetching all active team members")
                all_emails = self._lookup_all_member_emails(context)
                if all_emails:
                    recipients.update(all_emails)
                    log.append(f"Found {len(all_emails)} total member(s)")

        # ── Step 5: Fallback to current user ──
        if not recipients and context.get("user_id"):
            log.append("No recipients resolved — falling back to current user's email")
            try:
                from ..core.database import fetch_val
                user_email = self._run_async(
                    fetch_val("SELECT email FROM users WHERE id = $1", context["user_id"]),
                    context,
                )
                if user_email:
                    recipients.add(user_email)
                    log.append(f"Using current user's email: {user_email}")
            except Exception as e:
                log.append(f"Could not fetch user email: {e}")

        return list(recipients), log

    def _extract_team_name(self, text: str) -> Optional[str]:
        """
        Extract team name from natural language text using NLP patterns.

        Handles patterns like:
          - "send to engineering team"
          - "email the marketing team"
          - "share with backend team"
          - "send to all members in design team"
          - "notify the QA team"
          - "send report to engineering"
          - "email engineering department"
        """
        patterns = [
            # "send/email/share ... to/with [X] team"
            r'(?:send|email|share|forward|deliver|distribute|notify|inform|cc|broadcast)\s+(?:.*?\s+)?(?:to|with|for)\s+(?:all\s+(?:members?\s+(?:in|of|from)\s+)?)?(?:the\s+)?["\']?(\w[\w\s]*?)["\']?\s+team',
            # "[X] team members"
            r'(?:the\s+)?["\']?(\w[\w\s]*?)["\']?\s+team\s*(?:members?)?',
            # "team [X]"
            r'team\s+["\']?(\w[\w\s]*?)["\']?(?:\s|$|,|\.)',
            # "members of/in [X]"
            r'members?\s+(?:of|in|from)\s+(?:the\s+)?["\']?(\w[\w\s]*?)["\']?(?:\s+team)?(?:\s|$|,|\.)',
            # "send to [X] department"
            r'(?:send|email|share|forward)\s+(?:.*?\s+)?(?:to|with)\s+(?:the\s+)?["\']?(\w[\w\s]*?)["\']?\s+(?:department|group|division)',
            # "send/email to [known-team-name]" (without "team" suffix)
            # Catches: "send report to engineering", "email marketing"
            r'(?:send|email|share|forward|deliver|notify)\s+(?:.*?\s+)?(?:to|with)\s+(?:the\s+)?(\w+)(?:\s|$|,|\.)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                team = match.group(1).strip()
                # Filter out common false positives
                stop_words = {
                    "the", "a", "an", "my", "our", "your", "this", "that", "all",
                    "each", "every", "me", "him", "her", "them", "it", "report",
                    "summary", "file", "data", "csv", "pdf", "email", "message",
                    "result", "output", "analysis", "results",
                }
                if team.lower() not in stop_words and len(team) > 1:
                    return team

        return None

    def _extract_person_names(self, text: str) -> List[str]:
        """
        Extract person names from natural language text.
        Uses ORIGINAL-CASE text so capitalized name patterns match correctly.

        Handles patterns like:
          - "send to John"
          - "email Priyanshu"
          - "share the report with Aditya Singh"
          - "send it to priyanshu" (case-insensitive fallback)
        """
        names = []

        # Pattern 1: Capitalized names after action words (high confidence)
        capitalized_patterns = [
            # "send/email ... to [Name]" or "send/email ... to [First Last]"
            r'(?:send|email|share|forward|deliver|notify|inform)\s+(?:.*?\s+)?(?:to|with)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        ]

        for pattern in capitalized_patterns:
            matches = re.findall(pattern, text)
            for name in matches:
                name = name.strip()
                stop_words = {
                    "The", "All", "Each", "Every", "Team", "Members", "Everyone",
                    "File", "Report", "Summary", "Data", "Csv", "Pdf", "Email",
                }
                if name not in stop_words and len(name) > 1:
                    names.append(name)

        # Pattern 2: Case-insensitive fallback — catches "send to priyanshu"
        if not names:
            ci_patterns = [
                r'(?:send|email|share|forward|deliver|notify)\s+(?:.*?\s+)?(?:to|with)\s+([a-zA-Z]{3,}(?:\s+[a-zA-Z]{3,})?)',
            ]
            for pattern in ci_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for name in matches:
                    name = name.strip()
                    stop_words = {
                        "the", "all", "each", "every", "team", "members", "everyone",
                        "file", "report", "summary", "data", "csv", "pdf", "email",
                        "engineering", "marketing", "sales", "design", "backend",
                        "frontend", "devops", "results", "analysis", "output",
                        "message", "entire", "whole", "complete", "department",
                    }
                    if name.lower() not in stop_words and len(name) > 2:
                        names.append(name)

        return names

    # ─────────────────────────────────────────────
    # DATABASE LOOKUPS
    # ─────────────────────────────────────────────

    def _lookup_team_emails(self, team_name: str, context: Dict[str, Any]) -> List[str]:
        """Query team_members + teams tables to get all emails for a team."""
        try:
            from ..core.database import fetch_all
            rows = self._run_async(
                fetch_all(
                    """
                    SELECT DISTINCT tm.work_email
                    FROM team_members tm
                    JOIN teams t ON tm.team_id = t.id
                    WHERE (
                        LOWER(t.name) LIKE $1
                        OR LOWER(t.slug) LIKE $1
                        OR LOWER(tm.team_name) LIKE $1
                    )
                    AND tm.is_active = true
                    AND t.is_active = true
                    AND tm.work_email IS NOT NULL
                    AND tm.work_email != ''
                    """,
                    f"%{team_name.lower()}%",
                ),
                context,
            )
            return [row["work_email"] for row in rows if row["work_email"]]
        except Exception as e:
            logger.error(f"Team email lookup failed: {e}")
            return []

    def _lookup_person_email(self, person_name: str, context: Dict[str, Any]) -> Optional[str]:
        """Look up a person's email by name from team_members or users table."""
        try:
            from ..core.database import fetch_val

            # Try team_members first (has work_email — preferred for work comms)
            email = self._run_async(
                fetch_val(
                    """
                    SELECT tm.work_email
                    FROM team_members tm
                    JOIN users u ON tm.user_id = u.id
                    WHERE (
                        LOWER(u.full_name) LIKE $1
                        OR LOWER(tm.designation) LIKE $1
                    )
                    AND tm.is_active = true
                    AND tm.work_email IS NOT NULL
                    LIMIT 1
                    """,
                    f"%{person_name.lower()}%",
                ),
                context,
            )
            if email:
                return email

            # Fallback: try users table directly
            email = self._run_async(
                fetch_val(
                    """
                    SELECT email FROM users
                    WHERE LOWER(full_name) LIKE $1
                    AND is_active = true
                    LIMIT 1
                    """,
                    f"%{person_name.lower()}%",
                ),
                context,
            )
            return email

        except Exception as e:
            logger.error(f"Person email lookup failed for '{person_name}': {e}")
            return None

    def _lookup_all_member_emails(self, context: Dict[str, Any]) -> List[str]:
        """Get all active team member emails."""
        try:
            from ..core.database import fetch_all
            rows = self._run_async(
                fetch_all(
                    """
                    SELECT DISTINCT work_email
                    FROM team_members
                    WHERE is_active = true
                    AND work_email IS NOT NULL
                    AND work_email != ''
                    """
                ),
                context,
            )
            return [row["work_email"] for row in rows if row["work_email"]]
        except Exception as e:
            logger.error(f"All members lookup failed: {e}")
            return []

    # ─────────────────────────────────────────────
    # REPORT FILE DISCOVERY
    # ─────────────────────────────────────────────

    def _find_report_file(
        self,
        prev_results: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Discover the generated report file from previous tool results.

        Searches for:
          1. output_file path from csv_export_tool results
          2. File from data_summarizer_tool (written summary files)
          3. File from report_tool output
          4. The original uploaded file (if no generated output found)

        Returns:
            (file_path, file_name) or (None, None)
        """
        # Priority 1: Look for generated output files in previous tool results
        for agent_name, result in prev_results.items():
            if not isinstance(result, dict):
                continue

            # csv_export_tool writes analysed output files
            output_file = result.get("output_file")
            if output_file and os.path.isfile(output_file):
                return output_file, os.path.basename(output_file)

            # Check for any file_path in the result
            file_path = result.get("file_path")
            if file_path and os.path.isfile(file_path):
                return file_path, os.path.basename(file_path)

        # Priority 2: Look up the original uploaded file from DB
        file_id = context.get("file_id")
        if file_id:
            try:
                from ..core.database import fetch_one
                row = self._run_async(
                    fetch_one(
                        "SELECT file_name, file_path FROM files WHERE id = $1",
                        int(file_id),
                    ),
                    context,
                )
                if row and row["file_path"] and os.path.isfile(row["file_path"]):
                    return row["file_path"], row["file_name"]
            except Exception as e:
                logger.warning(f"Could not look up file {file_id}: {e}")

        return None, None

    # ─────────────────────────────────────────────
    # EMAIL BODY & SUBJECT GENERATION
    # ─────────────────────────────────────────────

    def _build_email_body(
        self,
        prev_results: Dict[str, Any],
        llm_summary: str,
        input_text: str,
    ) -> str:
        """Build plain-text email body from previous tool results (report, summary, etc.)."""
        parts = []
        parts.append("Hi,\n")
        parts.append("Please find the automated report generated by AutoOps AI below:\n")
        parts.append("=" * 60)

        # Priority 1: LLM-generated file summary (from data_summarizer_tool)
        for agent_name, result in prev_results.items():
            if isinstance(result, dict) and result.get("summary"):
                parts.append(f"\n📊 AI-Generated Summary\n")
                parts.append(result["summary"])
                if result.get("file_info"):
                    fi = result["file_info"]
                    parts.append(f"\n\nFile: {fi.get('name', 'N/A')} | Format: {fi.get('format', 'N/A')}")
                    if fi.get("rows"):
                        parts.append(f" | Rows: {fi['rows']}")
                    if fi.get("cols"):
                        parts.append(f" | Columns: {fi['cols']}")
                parts.append("")

        # Priority 2: Structured report (from report_tool)
        for agent_name, result in prev_results.items():
            if isinstance(result, dict) and result.get("report"):
                parts.append(f"\n{result['report']}")
                break

        # Priority 3: CSV analysis data (from csv_export_tool)
        for agent_name, result in prev_results.items():
            if isinstance(result, dict) and result.get("analysis"):
                analysis = result["analysis"]
                parts.append(f"\n📈 Data Analysis:")
                parts.append(f"  Rows: {analysis.get('total_rows', 'N/A')}")
                parts.append(f"  Columns: {analysis.get('total_columns', 'N/A')}")
                parts.append(f"  Missing Values: {analysis.get('missing_values', 'N/A')}")
                break

        # Fallback: use LLM summary from the email agent itself
        if len(parts) <= 3:
            if llm_summary:
                parts.append(f"\n{llm_summary}")
            else:
                parts.append("\nYour workflow has been completed successfully.")

        parts.append("\n" + "=" * 60)
        parts.append("\n— AutoOps AI | Automated Workflow Platform")

        return "\n".join(parts)

    def _build_html_body(self, plain_body: str, subject: str) -> str:
        """Convert the plain-text body into a styled HTML email."""
        # Escape HTML characters in the body text
        body_html = plain_body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # Convert newlines to <br> tags
        body_html = body_html.replace("\n", "<br>")
        # Bold the separator lines
        body_html = body_html.replace("=" * 60, "<hr style='border:1px solid #e0e0e0;'>")

        return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
             max-width: 700px; margin: 0 auto; padding: 20px; color: #333;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 12px; padding: 24px; margin-bottom: 24px; color: white;">
        <h1 style="margin: 0; font-size: 22px;">⚡ AutoOps AI Report</h1>
        <p style="margin: 8px 0 0; opacity: 0.9; font-size: 14px;">{subject}</p>
    </div>

    <div style="background: #fafafa; border-radius: 8px; padding: 20px;
                border: 1px solid #e8e8e8; line-height: 1.6; font-size: 14px;">
        {body_html}
    </div>

    <div style="margin-top: 24px; padding: 16px; background: #f0f4ff;
                border-radius: 8px; font-size: 12px; color: #555;">
        <p style="margin: 0;">This email was generated by <strong>AutoOps AI</strong> — Enterprise Workflow Automation Platform</p>
        <p style="margin: 4px 0 0; opacity: 0.7;">If a report file was generated, it is attached to this email.</p>
    </div>
</body>
</html>"""

    def _generate_subject(self, input_text: str, prev_results: Dict[str, Any]) -> str:
        """Generate a descriptive email subject from context."""
        # Check if there's a file name in previous results
        for agent_name, result in prev_results.items():
            if isinstance(result, dict) and result.get("file_info"):
                fname = result["file_info"].get("name", "")
                if fname:
                    return f"AutoOps AI Report — {fname}"

        # Derive from user prompt
        prompt_short = input_text[:60].strip()
        if prompt_short:
            return f"AutoOps AI — {prompt_short}"

        return "AutoOps AI — Automated Workflow Report"

    # ─────────────────────────────────────────────
    # SMTP SENDING (with file attachment support)
    # ─────────────────────────────────────────────

    @staticmethod
    def _send_smtp(
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_pass: str,
        to_email: str,
        subject: str,
        plain_body: str,
        html_body: str = "",
        attachment_path: Optional[str] = None,
        attachment_name: Optional[str] = None,
    ):
        """
        Send a single email via SMTP with optional file attachment.

        Sends a multipart/mixed email with:
          - Plain text fallback
          - HTML body (styled)
          - File attachment (if provided)
        """
        msg = MIMEMultipart("mixed")
        msg["From"] = f"AutoOps AI <{smtp_user}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        # Build the text/html alternative part
        text_part = MIMEMultipart("alternative")
        text_part.attach(MIMEText(plain_body, "plain", "utf-8"))
        if html_body:
            text_part.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(text_part)

        # Attach report file if available
        if attachment_path and os.path.isfile(attachment_path):
            try:
                with open(attachment_path, "rb") as f:
                    file_data = f.read()

                part = MIMEBase("application", "octet-stream")
                part.set_payload(file_data)
                encoders.encode_base64(part)

                fname = attachment_name or os.path.basename(attachment_path)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename=\"{fname}\"",
                )
                msg.attach(part)
                logger.info(f"Attached file: {fname} ({len(file_data)} bytes)")
            except Exception as e:
                logger.warning(f"Failed to attach file {attachment_path}: {e}")

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
