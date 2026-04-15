"""
CTDE Coordinator — Centralized Training, Decentralized Execution.

Implements the CTDE paradigm for multi-agent learning:
  - Centralized Training: Collects execution data from all agents,
    analyzes performance, and updates shared knowledge/policies.
  - Decentralized Execution: Each agent executes independently using
    policy hints derived from centralized learning.

The coordinator bridges execution feedback with the Learning Store
to enable continuous improvement across orchestration runs.
"""

import time
from typing import Any, Dict, List, Optional
from utils.logger import setup_logger
from adaptation.learning_store import LearningStore


class CTDECoordinator:
    """Centralized Training, Decentralized Execution coordinator.

    Collects execution data from all agents after a run, analyzes
    performance metrics, updates shared policies, and provides
    policy hints to future agents before execution.

    Attributes:
        learning_store: Persistent storage for policies and insights.
    """

    def __init__(self, learning_store: LearningStore) -> None:
        """Initialize the CTDE coordinator with a learning store."""
        self.logger = setup_logger("CTDECoordinator")
        self.learning_store = learning_store
        self.logger.info("CTDE Coordinator initialized.")

    def train_from_execution(
        self,
        scenario: str,
        agent_configs: List[Dict[str, Any]],
        results: List[Dict[str, Any]],
        performance_metrics: Dict[str, Any],
        dialogue_logs: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Analyze execution data and update shared policies.

        This is the 'centralized training' step — runs after every
        orchestration to extract learnings and improve future runs.

        Args:
            scenario: The executed scenario text.
            agent_configs: The agent configuration list (DAG structure).
            results: Per-agent execution results.
            performance_metrics: Timing and efficiency data.
            dialogue_logs: Optional multi-turn dialogue records.

        Returns:
            Dict with keys 'policies_updated' and 'insights_generated'.
        """
        self.logger.info("[CTDE TRAINING] Analyzing execution data...")

        updates = []
        agent_times = performance_metrics.get("agent_times_seconds", {})
        total_time = performance_metrics.get("total_time_seconds", 0)

        for result in results:
            agent_name = result.get("agent", "Unknown")
            status = result.get("status", "unknown")
            summary = result.get("summary", "")
            agent_time = agent_times.get(agent_name, 0)

            # Find matching config for this agent
            config = next(
                (c for c in agent_configs if c.get("name") == agent_name), {}
            )
            role = config.get("role", agent_name)

            policy_update = {
                "best_practices": [],
                "common_failures": [],
                "optimal_patterns": [],
            }

            if status == "completed":
                # Extract successful pattern
                practice = f"Successfully handled '{scenario[:60]}...' in {agent_time:.1f}s"
                policy_update["best_practices"].append(practice)

                # Identify optimal patterns from fast agents
                if agent_time < (total_time * 0.3) and total_time > 0:
                    pattern = f"Fast execution pattern: {summary[:80]}"
                    policy_update["optimal_patterns"].append(pattern)

            elif status == "failed":
                failure = f"Failed on '{scenario[:60]}...': {summary[:80]}"
                policy_update["common_failures"].append(failure)

            # Store policy for this role
            self.learning_store.store_policy(role, policy_update)
            self.logger.info(f"[CTDE TRAINING] Updated shared policy for: {role}")

            updates.append({
                "agent": agent_name,
                "role": role,
                "status": status,
                "policy_action": "updated",
            })

        # Generate execution insight
        insight = {
            "scenario": scenario[:100],
            "timestamp": time.time(),
            "agents_count": len(results),
            "success_rate": sum(
                1 for r in results if r.get("status") == "completed"
            ) / max(len(results), 1),
            "total_time": total_time,
            "efficiency_gain": performance_metrics.get("efficiency_gain_seconds", 0),
            "had_dialogues": bool(dialogue_logs),
            "dialogue_count": len(dialogue_logs) if dialogue_logs else 0,
        }
        self.learning_store.store_insight(insight)

        self.logger.info(
            f"[CTDE TRAINING] Complete — {len(updates)} policies updated, "
            f"insight stored (success rate: {insight['success_rate']:.0%})"
        )

        return {
            "policies_updated": updates,
            "insight": insight,
        }

    def get_shared_policy(self, agent_role: str) -> Dict[str, Any]:
        """Retrieve shared policy hints for a specific agent role.

        This is the 'decentralized execution' support — agents query
        this before executing to receive guidance from past learnings.

        Args:
            agent_role: The role to get policy hints for.

        Returns:
            Policy dict with best_practices, common_failures, optimal_patterns.
            Returns empty defaults if no policy exists.
        """
        policy = self.learning_store.get_policy(agent_role)

        if policy:
            self.logger.info(
                f"[CTDE POLICY] Providing policy hints for: {agent_role} "
                f"({len(policy.get('best_practices', []))} practices, "
                f"{len(policy.get('common_failures', []))} known failures)"
            )
            return policy

        self.logger.info(f"[CTDE POLICY] No prior policy for: {agent_role}")
        return {
            "best_practices": [],
            "common_failures": [],
            "optimal_patterns": [],
        }

    def get_all_policies_summary(self) -> Dict[str, Any]:
        """Return a summary of all stored CTDE policies."""
        all_policies = self.learning_store.get_all_policies()
        summary = {}
        for role, policy in all_policies.items():
            summary[role] = {
                "practices_count": len(policy.get("best_practices", [])),
                "failures_count": len(policy.get("common_failures", [])),
                "patterns_count": len(policy.get("optimal_patterns", [])),
            }
        return summary
