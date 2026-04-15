import json
from typing import Any, Dict, List, Optional
from utils.logger import setup_logger

# Tool catalog shared with the LLM — must stay in sync with llm_service.py SYSTEM_PROMPT
TOOL_CATALOG = """
AVAILABLE TOOLS (assign exactly one per agent via the "tool" field, or null if the agent only needs LLM reasoning):
- "csv_export_tool"   → Reads CSV/Excel files, performs statistical analysis, generates analyzed output file
- "email_tool"        → Sends emails via SMTP (requires recipient info)
- "email_reader_tool" → Reads/searches inbox emails via IMAP
- "slack_tool"        → Posts messages to Slack channels
- "zoom_tool"         → Creates Zoom video meetings
- "calendar_tool"     → Schedules meetings and manages calendar
- "sql_tool"          → Runs read-only SQL queries against a database
- "data_summarizer_tool" → Summarizes any file (CSV, Excel, JSON, TXT, PDF) using LLM — use when user asks to summarize/explain a file
- "report_tool"       → Generates a final structured summary report from all agent results (should be the LAST agent)
""".strip()

class WorkflowAdapter:
    """Adapts proven workflows to new scenarios using LLM entity substitution."""
    
    def __init__(self, llm_service):
        self.llm = llm_service
        self.logger = setup_logger("WorkflowAdapter")

    def adapt_workflow(
        self, 
        past_agent_configs: List[Dict[str, Any]], 
        old_scenario: str, 
        new_scenario: str,
        policy_hints: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Uses the LLM to intelligently modify role names, responsibilities, 
        and goals based on new scenario entities while preserving the DAG structure.
        Optionally includes CTDE policy hints for improved adaptation.
        """
        self.logger.info("Adapting past workflow to new scenario constraints...")
        
        # Phase 5: Build policy context if available
        policy_context = ""
        if policy_hints:
            policy_lines = []
            for role, policy in policy_hints.items():
                practices = policy.get("best_practices", [])[:2]
                failures = policy.get("common_failures", [])[:2]
                if practices or failures:
                    policy_lines.append(f"  {role}: Best practices: {practices}. Known failures: {failures}.")
            if policy_lines:
                policy_context = "\n\nCTDE LEARNED POLICIES (use these to improve the adaptation):\n" + "\n".join(policy_lines)
                self.logger.info(f"Including CTDE policy hints from {len(policy_hints)} roles.")
        
        prompt = f"""
        You are an expert System Architect. Your task is to adapt an existing multi-agent workflow 
        to fit a new scenario. You MUST strictly preserve the number of agents and their exact dependency structures.
        Only adapt the agent names (slightly, if needed), roles, and responsibilities to match the new context.
        
        {TOOL_CATALOG}
        
        IMPORTANT: Each agent in your response MUST include a "tool" field set to exactly one of the 
        tool names above, or null if no tool is needed. Assign tools based on what the agent actually 
        needs to do (e.g., analyzing CSV data → "csv_export_tool", generating report → "report_tool").
        
        OLD SCENARIO:
        {old_scenario}
        
        NEW SCENARIO:
        {new_scenario}
        
        PAST WORKFLOW GRAPH (JSON):
        {json.dumps(past_agent_configs, indent=2)}
        {policy_context}
        
        Provide your response as a valid JSON array matching the exact schema of the PAST WORKFLOW GRAPH.
        Every agent MUST have: "name", "role", "responsibilities", "dependencies", and "tool".
        Ensure every agent still explicitly declares the same 'dependencies' lists mapped to the new agent names.
        Return ONLY valid JSON.
        """
        
        # We use the generic adapt_graph function from the LLM service
        response = self.llm.adapt_graph(prompt)
        
        try:
            # Strip markdown formatting if any
            clean_json = response.replace("```json", "").replace("```", "").strip()
            adapted_configs = json.loads(clean_json)
            
            # Validate tool fields on adapted configs
            valid_tools = {
                "csv_export_tool", "email_tool", "email_reader_tool",
                "slack_tool", "zoom_tool", "calendar_tool",
                "sql_tool", "report_tool", "csv_tool", "data_summarizer_tool",
            }
            for agent in adapted_configs:
                tool = agent.get("tool")
                if tool in (None, "null", "none", "None", ""):
                    agent["tool"] = None
                elif isinstance(tool, str) and tool not in valid_tools:
                    self.logger.warning(f"Adapted agent '{agent.get('name')}' has unknown tool '{tool}', setting to None.")
                    agent["tool"] = None
            
            self.logger.info(f"Successfully adapted {len(adapted_configs)} agent configurations.")
            return adapted_configs
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode adapted JSON: {e}. Falling back to original configs.")
            # Fallback to the original configs if LLM fails formatting
            return past_agent_configs

