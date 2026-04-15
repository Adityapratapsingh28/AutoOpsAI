"""
Base Agent — Dynamic Agent Class for the Multi-Agent Orchestration Framework.

Represents a single dynamically created agent within the multi-agent system.
Agents are instantiated at runtime by the AgentFactory based on LLM-driven
scenario analysis. Each agent uses LLM reasoning augmented with memory
context to produce intelligent, scenario-specific execution results.
"""

from typing import Any, Dict, List

from utils.logger import setup_logger


class BaseAgent:
    """A dynamically instantiated agent in the orchestration framework.

    Each BaseAgent is created at runtime from the LLM's scenario analysis
    output. During execution, the agent calls the LLM with its role,
    responsibilities, and memory context from past similar scenarios to
    produce adaptive, intelligent responses.

    Attributes:
        name: The descriptive name of this agent.
        role: The functional role within the multi-agent ensemble.
        responsibilities: List of tasks this agent is responsible for.
        dependencies: List of agent names that must execute before this one.
        status: Current execution status ('pending', 'running', 'completed').
    """

    def __init__(
        self,
        name: str,
        role: str,
        responsibilities: List[str],
        dependencies: List[str],
    ) -> None:
        """Initialize a dynamically created agent.

        Args:
            name: The agent's descriptive name.
            role: The agent's functional role.
            responsibilities: Tasks assigned to this agent.
            dependencies: Names of agents that must run before this one.
        """
        self.name = name
        self.role = role
        self.responsibilities = responsibilities
        self.dependencies = dependencies
        self.status: str = "pending"
        # Phase 5: CTDE policy hints and dialogue history
        self.policy_hints: Dict[str, Any] = {}
        self.dialogue_history: List[Dict[str, Any]] = []
        self.logger = setup_logger(f"Agent:{self.name}")
        self.logger.info(
            f"Agent created — role='{self.role}', "
            f"responsibilities={self.responsibilities}, "
            f"dependencies={self.dependencies}"
        )

    def execute(
        self,
        context: Dict[str, Any],
        memory_context: List[str],
    ) -> Dict[str, Any]:
        """Execute this agent's assigned tasks using LLM reasoning.

        Calls the LLM service with the agent's role, responsibilities,
        current scenario, and relevant past execution memories to produce
        an intelligent, context-aware response.
        
        Reads any waiting messages via ACL message broker and logs output.

        Args:
            context: Contextual information from the orchestrator,
                     including the scenario and results from dependency agents.
            memory_context: Relevant past execution traces retrieved from
                            the vector store.

        Returns:
            A dictionary containing the agent name, completion status,
            and LLM-generated summary of actions taken.
        """
        from llm.llm_service import LLMService

        self.status = "running"
        self.logger.info(f"Executing with context keys: {list(context.keys())}")
        
        # Read incoming messages if bound
        if hasattr(self, "incoming_messages") and self.incoming_messages:
            self.logger.info(f"Incoming messages received: {len(self.incoming_messages)}")
            for msg in self.incoming_messages:
                self.logger.info(f"← [From {msg.sender}] {msg.performative}: {msg.content}")

        try:
            # Use LLM for reasoning — no hardcoded behavior
            llm_service = LLMService()
            
            # Phase 5: Enrich memory context with CTDE policy hints
            enriched_context = list(memory_context)
            if self.policy_hints:
                policy_text = (
                    f"CTDE Policy for {self.role}: "
                    f"Best practices: {', '.join(self.policy_hints.get('best_practices', [])[:3])}. "
                    f"Known failures: {', '.join(self.policy_hints.get('common_failures', [])[:2])}. "
                    f"Optimal patterns: {', '.join(self.policy_hints.get('optimal_patterns', [])[:2])}."
                )
                enriched_context.append(policy_text)
                self.logger.info(f"CTDE policy hints injected into reasoning context.")
            
            # Phase 5: Include dialogue history if available
            if self.dialogue_history:
                dialogue_text = f"Dialogue insights: {len(self.dialogue_history)} turns of coordination."
                enriched_context.append(dialogue_text)
            
            result = llm_service.reason_as_agent(
                name=self.name,
                role=self.role,
                responsibilities=self.responsibilities,
                scenario=context.get("scenario", ""),
                memory_context=enriched_context,
            )

            self.status = "completed"
            self.logger.info(f"Execution complete — {result.get('summary', 'done')[:50]}...")
            return result
            
        except Exception as e:
            self.status = "failed"
            self.logger.error(f"Agent execution failed: {e}")
            return {
                "agent": self.name,
                "status": "failed",
                "summary": f"Failed due to error: {str(e)}"
            }

    def __repr__(self) -> str:
        return (
            f"BaseAgent(name='{self.name}', role='{self.role}', "
            f"status='{self.status}')"
        )
