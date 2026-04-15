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
            body = self._build_email_body(prev_results, llm_summary, input_text, context)

        if not subject:
            subject = self._generate_subject(input_text, prev_results, context)

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

        # Sync to DB BEFORE sending actual emails so it acts as tracking
        self._sync_meeting_to_calendars(prev_results, recipients, context)

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
                "body_snippet": body[:1000] + "..." if len(body) > 1000 else body,
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
        team_names = self._extract_team_names(combined_lower)
        if team_names:
            for t_name in team_names:
                log.append(f"Team name detected: '{t_name}'")
                team_emails = self._lookup_team_emails(t_name, context)
                if team_emails:
                    recipients.update(team_emails)
                    log.append(f"Found {len(team_emails)} member(s) in team '{t_name}': {', '.join(team_emails)}")
                else:
                    log.append(f"No members found for team '{t_name}'")

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

    def _extract_team_names(self, text: str) -> List[str]:
        """
        Extract team name(s) from natural language text using NLP patterns.

        Handles patterns like:
          - "send to engineering team"
          - "email the marketing & management team"
          - "share with backend and frontend team"
          - "send report to engineering"
        """
        patterns = [
            # "send/email/share ... to/with [X] team"
            r'(?:send|email|share|forward|deliver|distribute|notify|inform|cc|broadcast)\s+(?:.*?\s+)?(?:to|with|for)\s+(?:all\s+(?:members?\s+(?:in|of|from)\s+)?)?(?:the\s+)?["\']?([\w\s,&]+?)["\']?\s+teams?',
            # "[X] team members"
            r'(?:the\s+)?["\']?([\w\s,&]+?)["\']?\s+teams?\s*(?:members?)?',
            # "team [X]"
            r'teams?\s+["\']?([\w\s,&]+?)["\']?(?:\s|$|,|\.)',
            # "members of/in [X]"
            r'members?\s+(?:of|in|from)\s+(?:the\s+)?["\']?([\w\s,&]+?)["\']?(?:\s+teams?)?(?:\s|$|,|\.)',
            # "send to [X] department"
            r'(?:send|email|share|forward)\s+(?:.*?\s+)?(?:to|with)\s+(?:the\s+)?["\']?([\w\s,&]+?)["\']?\s+(?:departments?|groups?|divisions?)',
            # "send/email to [known-team-name]" (without "team" suffix)
            r'(?:send|email|share|forward|deliver|notify)\s+(?:.*?\s+)?(?:to|with)\s+(?:the\s+)?([\w\s,&]+)(?:\s|$|,|\.)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                raw_team_str = match.group(1).strip()
                # Split by " and ", "&", ","
                parts = re.split(r'\s+and\s+|&|,', raw_team_str, flags=re.IGNORECASE)
                
                stop_words = {
                    "the", "a", "an", "my", "our", "your", "this", "that", "all",
                    "each", "every", "me", "him", "her", "them", "it", "report",
                    "summary", "file", "data", "csv", "pdf", "email", "message",
                    "result", "output", "analysis", "results", ""
                }
                
                found_teams = []
                for team in parts:
                    team = team.strip()
                    if team.lower() not in stop_words and len(team) > 1:
                        found_teams.append(team)
                        
                if found_teams:
                    return found_teams

        return []

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
        File attachment is disabled for now as per user request.
        """
        return None, None

    # ─────────────────────────────────────────────
    # EMAIL BODY & SUBJECT GENERATION
    # ─────────────────────────────────────────────

    def _build_email_body(
        self,
        prev_results: Dict[str, Any],
        llm_summary: str,
        input_text: str,
        context: Dict[str, Any],
    ) -> str:
        """Build plain-text email body from previous tool results (report, summary, etc.)."""
        parts = []
        
        # ── Fetch Sender Name ──
        # Priority 1: Pre-fetched by orchestrator and passed via context
        sender_name = context.get("sender_name", "")
        
        # Priority 2: Fallback — query DB directly using user_id from context
        if not sender_name:
            user_id = context.get("user_id")
            if user_id:
                try:
                    from ..core.database import fetch_val
                    name = self._run_async(fetch_val(
                        "SELECT full_name FROM users WHERE id = $1",
                        user_id
                    ), context)
                    if name:
                        sender_name = name
                except Exception as e:
                    logger.warning(f"Could not fetch sender name: {e}")
        
        if not sender_name:
            sender_name = "Your Manager"

        # ── PRIORITY: Is this a Meeting? (Calendly Style) ──
        has_meeting = False
        for agent_name, result in prev_results.items():
            if isinstance(result, dict) and result.get("meeting"):
                has_meeting = True
                mtg = result["meeting"]
                parts.append("Hi Team,\n")
                parts.append(f"{sender_name} wants to schedule a meet\n")
                parts.append(f"agenda is {mtg.get('topic', 'N/A')}\n")
                parts.append(f"time is {mtg.get('start_time', 'N/A')}\n")
                if mtg.get('duration'):
                    parts.append(f"duration is {mtg.get('duration')} mins\n")
                if mtg.get("join_url"):
                    parts.append(f"meeting link to join.. {mtg.get('join_url')}\n")
                if mtg.get('password'):
                    parts.append(f"meeting password: {mtg.get('password')}\n")
                parts.append("\nkindly join through that\n")
                parts.append("=" * 60)
                break

        if not has_meeting:
            parts.append(f"Hi Team,\n")
            parts.append(f"Please find the automated report generated by {sender_name} (via AutoOps AI) below:\n")
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

        # Priority 3 is handled above at the top for Calendly styling

        # Priority 3: CSV analysis data (from csv_export_tool)
        for agent_name, result in prev_results.items():
            if isinstance(result, dict) and result.get("analysis"):
                analysis = result["analysis"]
                parts.append(f"\n📈 Data Analysis:")
                parts.append(f"  Rows: {analysis.get('total_rows', 'N/A')}")
                parts.append(f"  Columns: {analysis.get('total_columns', 'N/A')}")
                parts.append(f"  Missing Values: {analysis.get('missing_values', 'N/A')}")
                
                insights = analysis.get("data_quality_insights")
                if insights:
                    parts.append("\n" + "-" * 80)
                    parts.append("  🚨 IMPORTANT INSIGHTS: DATA QUALITY")
                    parts.append("-" * 80)
                    parts.append("{:<20} | {:<20} | {}".format("COLUMN", "ISSUE", "RECOMMENDED RESOLUTION"))
                    parts.append("-" * 80)
                    for item in insights:
                        col_text = str(item['column'])[:18]
                        issue_text = str(item['issue'])[:18]
                        res_text = str(item['resolution'])
                        parts.append("{:<20} | {:<20} | {}".format(col_text, issue_text, res_text))
                    parts.append("-" * 80 + "\n")
                
                break

        # Fallback: use LLM summary only if nothing meaningful was built
        # (i.e. no meeting, no report, no summary, no analysis)
        if not has_meeting and len(parts) <= 3:
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
                border: 1px solid #e8e8e8; line-height: 1.6; font-size: 14px; white-space: pre-wrap; font-family: ui-monospace, Menlo, Monaco, 'Courier New', monospace;">
        {body_html}
    </div>

    <div style="margin-top: 24px; padding: 16px; background: #f0f4ff;
                border-radius: 8px; font-size: 12px; color: #555;">
        <p style="margin: 0;">This email was generated by <strong>AutoOps AI</strong> — Enterprise Workflow Automation Platform</p>
    </div>
</body>
</html>"""

    def _sync_meeting_to_calendars(self, prev_results: Dict[str, Any], recipients: List[str], context: Dict[str, Any]):
        """Detect if meeting was scheduled and sync it to the calendars of all users involved."""
        from datetime import datetime
        mtg = None
        for agent_name, result in prev_results.items():
            if isinstance(result, dict) and result.get("meeting"):
                mtg = result["meeting"]
                break
                
        if not mtg:
            return
            
        topic = mtg.get("topic", "AutoOps Generated Meeting")
        start_time = mtg.get("start_time")
        join_url = mtg.get("join_url", "")
        
        if not start_time:
            return
            
        try:
            from ..core.database import fetch_all, execute
            
            # 1. Gather all target user IDs
            target_ids = set()
            sender_id = context.get("user_id")
            if sender_id:
                target_ids.add(sender_id)
                
            if recipients:
                # Find DB users matching these emails
                placeholders = ", ".join(f"${i+1}" for i in range(len(recipients)))
                if placeholders:
                    query = f"SELECT id FROM users WHERE email IN ({placeholders})"
                    rows = self._run_async(fetch_all(query, *recipients), context)
                    for row in rows:
                        target_ids.add(row["id"])
                        
            # 2. Insert into meetings table for each user
            for u_id in target_ids:
                # Basic dedup based on title and time
                is_duplicate = self._run_async(fetch_all(
                    "SELECT id FROM meetings WHERE user_id = $1 AND title = $2 AND time = $3",
                    u_id, topic, start_time
                ), context)
                
                if not is_duplicate:
                    self._run_async(execute(
                        "INSERT INTO meetings (user_id, title, time, meeting_link) VALUES ($1, $2, $3, $4)",
                        u_id, topic, start_time, join_url
                    ), context)
                    
            logger.info(f"Synced meeting to {len(target_ids)} calendar(s).")
        except Exception as e:
            logger.warning(f"Failed to sync meeting to calendars: {e}")

    def _generate_subject(self, input_text: str, prev_results: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """Generate a professional email subject.
        
        For meetings: 'Meeting Invitation: <Topic> | <Date>'
        For reports:  'AutoOps Report — <File/Topic>'
        """
        from datetime import datetime
        context = context or {}
        sender = context.get("sender_name", "")

        # ── Meeting subject ──
        for agent_name, result in prev_results.items():
            if isinstance(result, dict) and result.get("meeting"):
                mtg = result["meeting"]
                topic = mtg.get("topic", "Team Meeting")
                start_time = mtg.get("start_time", "")
                
                # Format date nicely: "Wed, Apr 16"
                date_str = ""
                if start_time:
                    try:
                        dt = datetime.strptime(start_time[:19], "%Y-%m-%dT%H:%M:%S")
                        date_str = f" | {dt.strftime('%a, %b %d')}"
                    except Exception:
                        pass
                
                prefix = f"{sender} invites you" if sender else "Meeting Invitation"
                return f"{prefix}: {topic}{date_str}"

        # ── File report subject ──
        for agent_name, result in prev_results.items():
            if isinstance(result, dict) and result.get("file_info"):
                fname = result["file_info"].get("name", "")
                if fname:
                    prefix = f"{sender}'s Report" if sender else "AutoOps AI Report"
                    return f"{prefix} — {fname}"

        # ── Generic subject ──
        # Extract a meaningful short phrase from the prompt
        prompt_clean = input_text.strip()
        # Remove filler prefixes
        for filler in ["i need to ", "i want to ", "please ", "can you ", "could you "]:
            if prompt_clean.lower().startswith(filler):
                prompt_clean = prompt_clean[len(filler):]
                break
        prompt_short = prompt_clean[:55].strip().rstrip(",.:;")
        if prompt_short:
            prefix = f"Action from {sender}" if sender else "AutoOps AI"
            return f"{prefix}: {prompt_short.capitalize()}"

        return f"{'Action Required' if not sender else f'Message from {sender}'} — AutoOps AI"

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
