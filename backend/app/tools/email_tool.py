"""
AutoOps AI — Email Tool.

Sends emails via SMTP with smart recipient resolution.
Supports:
  - Direct email addresses
  - Team-based lookup ("send to engineering team")
  - Person name lookup ("send to John", "send to Priyanshu")
  - Uses previous_tool_results to attach generated reports/summaries
"""

import re
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict, List, Optional, Tuple

from .base_tool import BaseTool

logger = logging.getLogger("autoops.tools.email")


class EmailTool(BaseTool):
    name = "email_tool"
    description = "Sends emails via SMTP with team/person resolution from database"

    def run(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send an email with smart recipient resolution.

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

        # ── 3. Send emails ──
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
                    body=body,
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
          2. Team name → lookup team_members table
          3. Person name → lookup team_members/users table
          4. Fallback to user's own email

        Returns:
            (list of email addresses, resolution log messages)
        """
        log = []
        recipients = set()
        combined_text = f"{input_text} {llm_summary}".lower()

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
        team_name = self._extract_team_name(combined_text)
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
            person_names = self._extract_person_names(combined_text)
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
            all_keywords = ["all members", "everyone", "all employees", "all team members", "all teams", "entire team"]
            if any(kw in combined_text for kw in all_keywords):
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
        """
        # Pattern: "[action] ... [team_name] team"
        patterns = [
            # "send/email/share ... to/with [X] team"
            r'(?:send|email|share|forward|deliver|distribute|notify|inform|cc|broadcast)\s+(?:.*?\s+)?(?:to|with|for)\s+(?:all\s+(?:members?\s+(?:in|of|from)\s+)?)?(?:the\s+)?["\']?(\w[\w\s]*?)["\']?\s+team',
            # "[X] team members"
            r'(?:the\s+)?["\']?(\w[\w\s]*?)["\']?\s+team\s*(?:members?)?',
            # "team [X]"
            r'team\s+["\']?(\w[\w\s]*?)["\']?(?:\s|$|,|\.)',
            # "members of/in [X]"
            r'members?\s+(?:of|in|from)\s+(?:the\s+)?["\']?(\w[\w\s]*?)["\']?(?:\s+team)?(?:\s|$|,|\.)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                team = match.group(1).strip()
                # Filter out common false positives
                stop_words = {"the", "a", "an", "my", "our", "your", "this", "that", "all", "each", "every"}
                if team.lower() not in stop_words and len(team) > 1:
                    return team

        return None

    def _extract_person_names(self, text: str) -> List[str]:
        """
        Extract person names from natural language text.

        Handles patterns like:
          - "send to John"
          - "email Priyanshu"
          - "share the report with Aditya"
        """
        names = []

        patterns = [
            # "send/email ... to [Name]"
            r'(?:send|email|share|forward|deliver|notify)\s+(?:.*?\s+)?(?:to|with)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        ]

        # Run on original-case text for proper name detection
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for name in matches:
                name = name.strip()
                # Filter out common false positives
                stop_words = {"the", "all", "each", "every", "team", "members", "everyone",
                              "file", "report", "summary", "data", "csv", "email"}
                if name.lower() not in stop_words and len(name) > 1:
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

            # Try team_members first (has work_email)
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
    # EMAIL BODY & SUBJECT GENERATION
    # ─────────────────────────────────────────────

    def _build_email_body(
        self,
        prev_results: Dict[str, Any],
        llm_summary: str,
        input_text: str,
    ) -> str:
        """Build email body from previous tool results (report, summary, etc.)."""
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
    # SMTP SENDING
    # ─────────────────────────────────────────────

    @staticmethod
    def _send_smtp(
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_pass: str,
        to_email: str,
        subject: str,
        body: str,
    ):
        """Send a single email via SMTP."""
        msg = MIMEMultipart("alternative")
        msg["From"] = smtp_user
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
