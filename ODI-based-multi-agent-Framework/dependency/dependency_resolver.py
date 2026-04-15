"""
Dependency Resolver — Agent Execution Order Computation.

Builds a dependency graph from agent configurations and performs
topological sorting to determine the correct execution order.
Detects and raises errors on circular dependencies.
"""

from collections import defaultdict, deque
from typing import Any, Dict, List

from utils.logger import setup_logger


class DependencyResolver:
    """Resolves agent execution order based on declared dependencies.

    Constructs a directed acyclic graph (DAG) from agent dependency
    declarations and performs Kahn's algorithm (BFS-based topological
    sort) to compute a valid execution sequence.

    Raises an error if circular dependencies are detected.
    """

    def __init__(self) -> None:
        """Initialize the dependency resolver."""
        self.logger = setup_logger("DependencyResolver")

    def resolve(self, agent_configs: List[Dict[str, Any]]) -> List[str]:
        """Compute the execution order for a set of agents.

        Args:
            agent_configs: List of agent configuration dictionaries,
                           each containing 'name' and 'dependencies'.

        Returns:
            An ordered list of agent names representing the execution
            sequence (dependencies first).

        Raises:
            ValueError: If a circular dependency is detected.
        """
        self.logger.info(f"Resolving dependencies for {len(agent_configs)} agents.")

        # Build the graph
        all_agents = {cfg["name"] for cfg in agent_configs}
        graph: Dict[str, List[str]] = defaultdict(list)  # adj list: dep -> dependents
        in_degree: Dict[str, int] = {name: 0 for name in all_agents}

        for cfg in agent_configs:
            agent_name = cfg["name"]
            for dep in cfg["dependencies"]:
                # Only consider dependencies that are within our agent set
                if dep in all_agents:
                    graph[dep].append(agent_name)
                    in_degree[agent_name] += 1
                else:
                    self.logger.warning(
                        f"Agent '{agent_name}' depends on '{dep}' which is "
                        f"not in the agent set — skipping."
                    )

        # Kahn's algorithm — BFS topological sort
        queue: deque = deque()
        for name in all_agents:
            if in_degree[name] == 0:
                queue.append(name)

        execution_order: List[str] = []

        while queue:
            current = queue.popleft()
            execution_order.append(current)

            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Check for circular dependencies
        if len(execution_order) != len(all_agents):
            remaining = all_agents - set(execution_order)
            raise ValueError(
                f"Circular dependency detected among agents: {remaining}"
            )

        self.logger.info(f"Execution order resolved: {execution_order}")
        return execution_order
