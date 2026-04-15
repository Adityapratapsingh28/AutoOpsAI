"""
Agent Factory — Dynamic Agent Instantiation.

Creates BaseAgent instances from LLM-generated configuration dictionaries.
Each agent's identity and capabilities are determined entirely at runtime
based on the scenario analysis output.
"""

from typing import Any, Dict

from agents.base_agent import BaseAgent
from utils.logger import setup_logger


def create_agent(agent_config: Dict[str, Any]) -> BaseAgent:
    """Instantiate a BaseAgent from an LLM-generated configuration.

    Args:
        agent_config: A dictionary containing the agent specification
                      with keys: 'name', 'role', 'responsibilities',
                      'dependencies'.

    Returns:
        A fully initialized BaseAgent instance.

    Raises:
        KeyError: If required keys are missing from agent_config.
    """
    logger = setup_logger("AgentFactory")

    agent = BaseAgent(
        name=agent_config["name"],
        role=agent_config["role"],
        responsibilities=agent_config["responsibilities"],
        dependencies=agent_config["dependencies"],
    )

    logger.info(f"Created agent: {agent.name} (role={agent.role})")
    return agent
