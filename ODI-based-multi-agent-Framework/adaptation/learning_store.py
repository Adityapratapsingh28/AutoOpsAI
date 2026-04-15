"""
Learning Store — Persistent Policy & Insight Storage for CTDE.

Stores learned policies (best practices, common failures, optimal patterns)
and execution insights as JSON files. Used by the CTDE Coordinator to
persist knowledge across runs and provide guidance to future agents.
"""

import json
import os
from typing import Any, Dict, List, Optional
from utils.logger import setup_logger


class LearningStore:
    """Persistent JSON-based storage for CTDE policies and execution insights.

    Attributes:
        storage_dir: Directory path for storing JSON data files.
        policies: Dict mapping agent roles to their learned policies.
        insights: List of accumulated execution insights.
    """

    def __init__(self, storage_dir: str = "learning_data") -> None:
        """Initialize the learning store, loading existing data if available."""
        self.logger = setup_logger("LearningStore")
        self.storage_dir = storage_dir
        self.policies_file = os.path.join(storage_dir, "policies.json")
        self.insights_file = os.path.join(storage_dir, "insights.json")

        os.makedirs(storage_dir, exist_ok=True)

        self.policies: Dict[str, Dict[str, List]] = self._load_json(self.policies_file, {})
        self.insights: List[Dict[str, Any]] = self._load_json(self.insights_file, [])

        self.logger.info(
            f"Learning Store initialized — {len(self.policies)} policies, "
            f"{len(self.insights)} insights loaded."
        )

    def _load_json(self, filepath: str, default: Any) -> Any:
        """Load JSON from file, returning default if not found."""
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(f"Failed to load {filepath}: {e}")
        return default

    def _save_json(self, filepath: str, data: Any) -> None:
        """Persist data as JSON to file."""
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except IOError as e:
            self.logger.error(f"Failed to save {filepath}: {e}")

    def store_policy(self, agent_role: str, policy_data: Dict[str, Any]) -> None:
        """Store or update a learned policy for a specific agent role.

        Args:
            agent_role: The role identifier (e.g., 'Evacuation Coordinator').
            policy_data: Dict with keys like 'best_practices', 'common_failures',
                         'optimal_patterns'.
        """
        if agent_role not in self.policies:
            self.policies[agent_role] = {
                "best_practices": [],
                "common_failures": [],
                "optimal_patterns": [],
            }

        existing = self.policies[agent_role]

        # Merge new data into existing, avoiding duplicates
        for key in ["best_practices", "common_failures", "optimal_patterns"]:
            new_items = policy_data.get(key, [])
            for item in new_items:
                if item not in existing[key]:
                    existing[key].append(item)

        self._save_json(self.policies_file, self.policies)
        self.logger.info(f"[LEARNING STORE] Policy updated for role: {agent_role}")

    def get_policy(self, agent_role: str) -> Optional[Dict[str, Any]]:
        """Retrieve learned policy for a given agent role.

        Args:
            agent_role: The role to look up.

        Returns:
            Policy dict or None if no policy exists for this role.
        """
        return self.policies.get(agent_role)

    def store_insight(self, insight: Dict[str, Any]) -> None:
        """Append an execution insight to the persistent store.

        Args:
            insight: Dict containing scenario, outcome, metrics, learnings, etc.
        """
        self.insights.append(insight)
        self._save_json(self.insights_file, self.insights)
        self.logger.info(f"[LEARNING STORE] New insight stored (total: {len(self.insights)})")

    def get_insights(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent execution insights.

        Args:
            limit: Max number of recent insights to return.

        Returns:
            List of insight dicts, most recent last.
        """
        return self.insights[-limit:]

    def get_all_policies(self) -> Dict[str, Dict[str, Any]]:
        """Return all stored policies."""
        return self.policies
