"""
Agent Registry — Centralized Agent Storage and Lookup.

Provides a registry for tracking all dynamically created agents within
a scenario execution. Supports registration, retrieval by name, and
listing of all active agents.
"""

from typing import Dict, List, Optional

from agents.base_agent import BaseAgent
from utils.logger import setup_logger


class AgentRegistry:
    """Centralized registry for managing dynamically created agents.

    Stores agents by name for O(1) lookup and provides enumeration
    of the full agent ensemble.

    Attributes:
        _agents: Internal dictionary mapping agent names to instances.
    """

    def __init__(self) -> None:
        """Initialize an empty agent registry."""
        self._agents: Dict[str, BaseAgent] = {}
        self.logger = setup_logger("AgentRegistry")
        self.logger.info("Agent Registry initialized.")

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent in the registry.

        Args:
            agent: The BaseAgent instance to register.

        Raises:
            ValueError: If an agent with the same name is already registered.
        """
        if agent.name in self._agents:
            raise ValueError(
                f"Agent '{agent.name}' is already registered."
            )
        self._agents[agent.name] = agent
        self.logger.info(f"Registered agent: {agent.name}")

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Retrieve an agent by name.

        Args:
            name: The name of the agent to retrieve.

        Returns:
            The BaseAgent instance, or None if not found.
        """
        return self._agents.get(name)

    def list_agents(self) -> List[BaseAgent]:
        """Return all registered agents.

        Returns:
            A list of all BaseAgent instances in the registry.
        """
        return list(self._agents.values())

    def __len__(self) -> int:
        return len(self._agents)
