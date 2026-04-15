"""
Short-Term Memory — Session-Scoped Execution State.

Provides transient in-memory storage for agent outputs and intermediate
state within a single scenario execution cycle. This memory is discarded
after each run — persistent memory is handled by the VectorStore.
"""

from typing import Any, Dict, List, Optional

from utils.logger import setup_logger


class ShortTermMemory:
    """In-memory session state for a single scenario execution.

    Tracks agent outputs and intermediate state during orchestration.
    Cleared between runs — not persisted.

    Attributes:
        scenario: The current scenario being executed.
        agent_outputs: Dictionary of agent_name -> execution output.
        intermediate_state: Dictionary for arbitrary intermediate data.
    """

    def __init__(self, scenario: str = "") -> None:
        """Initialize short-term memory for a scenario session.

        Args:
            scenario: The scenario text for this execution session.
        """
        self.scenario: str = scenario
        self.agent_outputs: Dict[str, Dict[str, Any]] = {}
        self.intermediate_state: Dict[str, Any] = {}
        self.logger = setup_logger("ShortTermMemory")
        self.logger.info("Short-term memory initialized.")

    def store_agent_output(
        self, agent_name: str, output: Dict[str, Any]
    ) -> None:
        """Store the execution output of an agent.

        Args:
            agent_name: The name of the agent.
            output: The agent's execution result dictionary.
        """
        self.agent_outputs[agent_name] = output
        self.logger.debug(f"Stored output for agent: {agent_name}")

    def get_agent_output(
        self, agent_name: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve the execution output of a specific agent.

        Args:
            agent_name: The name of the agent.

        Returns:
            The agent's output dictionary, or None if not found.
        """
        return self.agent_outputs.get(agent_name)

    def get_all_outputs(self) -> Dict[str, Dict[str, Any]]:
        """Return all stored agent outputs.

        Returns:
            Dictionary mapping agent names to their outputs.
        """
        return dict(self.agent_outputs)
