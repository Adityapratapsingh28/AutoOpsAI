"""
LLM Service — Language Model Integration for Scenario Analysis.

Provides an interface to LLM providers (Groq / OpenAI) for analyzing
scenario descriptions and determining the required multi-agent ensemble.
The service sends a structured prompt and parses the LLM's JSON response
into agent configuration data.
"""

import json
import re
from typing import Any, Dict, List

from openai import OpenAI

from utils.config import Config
from utils.logger import setup_logger

# System prompt for multi-agent architecture design
SYSTEM_PROMPT = """You are a multi-agent system architect for an enterprise automation platform.

Given a scenario, design a dynamic multi-agent system that uses specialized tools to complete real tasks.

AVAILABLE TOOLS (assign exactly one per agent, or null if the agent only needs LLM reasoning):
- "csv_export_tool"        → Reads CSV/Excel files, performs statistical analysis, generates analyzed output file
- "data_summarizer_tool"   → Summarizes any file (CSV, Excel, JSON, TXT, PDF) using LLM — use when user asks to summarize/explain/describe a file
- "email_tool"             → Sends emails via SMTP with FILE ATTACHMENT support. Capabilities:
                              • NLP Recipient Resolution (auto-detects from natural language):
                                - Team-based: "send to engineering team", "email marketing team", "notify QA" → looks up teams + team_members table
                                - Person-based: "send to Priyanshu", "email John", "forward to Aditya" → looks up user by name in team_members/users
                                - Direct email: "send to john@example.com" → sends directly
                                - All members: "send to everyone", "notify all employees" → all active team members
                              • Auto-Attachment: Automatically discovers and attaches generated report/analysis files from previous agents
                              • Auto-Content: Builds email body from previous tool results (summaries, analysis, reports)
                              • If user says ANYTHING about sending/emailing/forwarding/sharing/notifying a report/summary/file to someone, assign this tool
- "email_reader_tool"      → Reads/searches inbox emails via IMAP
- "slack_tool"             → Posts messages to Slack channels
- "zoom_tool"              → Creates Zoom video meetings
- "calendar_tool"          → Schedules meetings and manages calendar
- "sql_tool"               → Runs read-only SQL queries against a database
- "report_tool"            → Generates a final structured summary report from all agent results (should be the LAST agent)

DATABASE CONTEXT (available for email_tool recipient resolution):
- "teams" table: id, name, slug, description, is_active
- "team_members" table: user_id, team_id, team_name, work_email, phone_number, designation, role, is_active
- "users" table: id, full_name, email, role, is_active

EMAIL INTENT EXAMPLES (when ANY of these patterns appear, the LLM must assign "email_tool"):
- "send the report to engineering team"
- "email the summary to Priyanshu"
- "share this with the backend team"
- "forward the analysis to all members"
- "notify the design team about this"
- "send it to john@company.com"
- "email everyone the results"
- "send the generated file to QA team"
- "summarize and send to marketing"
- "analyze and email to Aditya"

Return strictly valid JSON with:

{
  "agents": [
    {
      "name": "...",
      "role": "...",
      "tool": "tool_name_here or null",
      "responsibilities": ["..."],
      "dependencies": ["..."]
    }
  ]
}

IMPORTANT RULES:
- "tool" must be exactly one of the available tool names listed above, or null if no tool is needed.
- Every workflow MUST have at least one agent that uses a real tool. Do NOT create agents that all have null tools.
- If the user mentions analyzing a file/CSV/data, assign "csv_export_tool" to the analysis agent.
- If the user asks to summarize, explain, or describe a file, assign "data_summarizer_tool".
- If the user asks to email/send/forward/share/notify a report/summary/file to a team, person, or email address, assign "email_tool" to an email agent.
  ALWAYS include the target recipient (team name, person name, or email) in the agent's responsibilities.
  Example: "Send the generated report with file attachment to the engineering team"
  The email_tool will auto-resolve recipients from the database, build the email body from prior results, and attach any generated files.
- If multiple tasks are requested (e.g., summarize + email), create separate agents for each with the appropriate tool.
  The email agent MUST depend on the summarizer/analysis agent so it receives the output content and files to send.
- The last agent should typically use "report_tool" to compile a final summary. Place the email agent BEFORE the report agent if emailing is requested.
- "dependencies" must ONLY contain names of OTHER agents in the list.
- Do NOT create circular dependencies. Dependencies must form a valid DAG.
- At least one agent must have an empty dependencies list (the starting agent).
- Keep agent count minimal (2-5 agents). Do NOT over-engineer with unnecessary agents.

Return only JSON. No explanation, no markdown, no code fences."""



class LLMService:
    """Interface to LLM providers for scenario-driven agent design.

    Uses the OpenAI-compatible API to communicate with Groq or OpenAI.
    Sends scenario text with a structured system prompt and parses the
    response into validated agent configuration JSON.

    Attributes:
        client: An OpenAI client instance configured for the selected provider.
        model: The model identifier to use for completions.
    """

    def __init__(self) -> None:
        """Initialize the LLM service with provider-specific configuration."""
        self.logger = setup_logger("LLMService")

        if Config.LLM_PROVIDER == "groq":
            base_url = "https://api.groq.com/openai/v1"
            api_key = Config.GROQ_API_KEY
        else:
            base_url = None
            api_key = Config.GROQ_API_KEY  # fallback

        if not api_key:
            raise ValueError(
                "API key not found. Set GROQ_API_KEY in your .env file."
            )

        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = Config.LLM_MODEL
        self.logger.info(
            f"LLM Service initialized (provider={Config.LLM_PROVIDER}, "
            f"model={self.model})."
        )

    def analyze_scenario(self, scenario_text: str) -> List[Dict[str, Any]]:
        """Send a scenario to the LLM and return parsed agent configurations.

        Args:
            scenario_text: A natural-language description of the scenario.

        Returns:
            A list of agent configuration dictionaries, each containing
            'name', 'role', 'responsibilities', and 'dependencies'.

        Raises:
            ValueError: If the LLM response is not valid JSON or does not
                        conform to the expected schema.
        """
        self.logger.info(f"Sending scenario to LLM: {scenario_text}")

        user_prompt = f"Scenario:\n{scenario_text}\n\nReturn only JSON."

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )

        raw_content = response.choices[0].message.content.strip()
        self.logger.debug(f"Raw LLM response: {raw_content}")

        # Parse JSON from the response
        parsed = self._parse_json(raw_content)
        self._validate_structure(parsed)

        agents = parsed["agents"]
        self.logger.info(f"LLM proposed {len(agents)} agent(s).")
        return agents

    def _parse_json(self, raw: str) -> Dict[str, Any]:
        """Extract and parse JSON from the LLM response string.

        Handles cases where the LLM wraps JSON in markdown code fences.

        Args:
            raw: The raw text response from the LLM.

        Returns:
            The parsed JSON as a dictionary.

        Raises:
            ValueError: If no valid JSON can be extracted.
        """
        # Try direct parse first
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code fences
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try finding JSON object in the text
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        raise ValueError(
            f"Failed to parse valid JSON from LLM response:\n{raw}"
        )

    def _validate_structure(self, data: Dict[str, Any]) -> None:
        """Validate that the parsed JSON conforms to the expected schema.

        Args:
            data: The parsed JSON dictionary.

        Raises:
            ValueError: If the structure is invalid.
        """
        if "agents" not in data:
            raise ValueError("LLM response missing 'agents' key.")

        if not isinstance(data["agents"], list) or len(data["agents"]) == 0:
            raise ValueError("'agents' must be a non-empty list.")

        valid_tools = {
            "csv_export_tool", "email_tool", "email_reader_tool",
            "slack_tool", "zoom_tool", "calendar_tool",
            "sql_tool", "report_tool", "csv_tool", "data_summarizer_tool",
        }

        required_keys = {"name", "role", "responsibilities", "dependencies"}
        for i, agent in enumerate(data["agents"]):
            if not isinstance(agent, dict):
                raise ValueError(f"Agent at index {i} is not a dictionary.")
            missing = required_keys - set(agent.keys())
            if missing:
                raise ValueError(
                    f"Agent '{agent.get('name', f'index {i}')}' is missing "
                    f"required keys: {missing}"
                )
            if not isinstance(agent["responsibilities"], list):
                raise ValueError(
                    f"Agent '{agent['name']}': 'responsibilities' must be a list."
                )
            if not isinstance(agent["dependencies"], list):
                raise ValueError(
                    f"Agent '{agent['name']}': 'dependencies' must be a list."
                )

            # Normalize tool field — accept null, None, or missing as None
            tool = agent.get("tool")
            if tool in (None, "null", "none", "None", ""):
                agent["tool"] = None
            elif isinstance(tool, str) and tool not in valid_tools:
                self.logger.warning(
                    f"Agent '{agent['name']}' has unknown tool '{tool}', setting to None."
                )
                agent["tool"] = None

    def reason_as_agent(
        self,
        name: str,
        role: str,
        responsibilities: List[str],
        scenario: str,
        memory_context: List[str],
    ) -> Dict[str, Any]:
        """Generate LLM-driven reasoning for an individual agent's execution.

        Args:
            name: The agent's name.
            role: The agent's functional role.
            responsibilities: The agent's assigned tasks.
            scenario: The current scenario description.
            memory_context: Relevant past execution traces.

        Returns:
            A dictionary with 'agent', 'status', and 'summary' keys.
        """
        self.logger.info(f"Generating LLM reasoning for agent: {name}")

        memory_text = "\n".join(memory_context) if memory_context else "None"
        responsibilities_text = "\n".join(f"- {r}" for r in responsibilities)

        agent_prompt = f"""You are an AI agent executing a task in a multi-agent system.

Previous related cases:
{memory_text}

Current scenario:
{scenario}

Your role: {role}
Your name: {name}

Your responsibilities:
{responsibilities_text}

Based on the scenario and any relevant past cases, describe what actions you would take to fulfill your responsibilities. Be specific  and practical.

Return strictly valid JSON:
{{
  "agent": "{name}",
  "status": "completed",
  "summary": "A specific summary of actions taken by this agent"
}}

Return only JSON. No explanation, no markdown, no code fences."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a specialized AI agent in a multi-agent system. Respond only with valid JSON."},
                {"role": "user", "content": agent_prompt},
            ],
            temperature=0.4,
        )

        raw_content = response.choices[0].message.content.strip()
        self.logger.debug(f"Agent '{name}' raw LLM response: {raw_content}")

        try:
            result = self._parse_json(raw_content)
            # Ensure required keys exist
            result.setdefault("agent", name)
            result.setdefault("status", "completed")
            result.setdefault("summary", f"{name} completed assigned tasks.")
            return result
        except ValueError:
            self.logger.warning(
                f"Failed to parse agent '{name}' response, using fallback."
            )
            return {
                "agent": name,
                "status": "completed",
                "summary": f"{name} ({role}) completed: {', '.join(responsibilities)}",
            }

    def adapt_graph(self, prompt: str) -> str:
        """Call LLM directly to adapt an existing workflow graph."""
        self.logger.info("Calling LLM to adapt workflow graph based on new scenario...")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a JSON-only API. Only output raw JSON arrays."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
