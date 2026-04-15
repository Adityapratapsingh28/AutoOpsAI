from typing import Any, Dict, List
from memory.vector_store import VectorStore
from utils.logger import setup_logger

class FeedbackLoop:
    """Adjusts confidence scores and evaluates execution for CTDE training."""
    
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.logger = setup_logger("FeedbackLoop")
        
    def penalize_experience(self, experience_id: str, current_metadata: dict, penalty_factor: float = 0.8):
        """
        Reduces the confidence score of a past experience if an adapted run fails.
        Prevents the system from repeatedly reusing a fundamentally flawed workflow.
        """
        current_confidence = float(current_metadata.get("confidence_score", 1.0))
        new_confidence = max(0.1, current_confidence * penalty_factor)
        
        current_metadata["confidence_score"] = new_confidence
        
        self.vector_store.update_execution_metadata(experience_id, current_metadata)
        
        self.logger.warning(
            f"Penalized experience '{experience_id}'. "
            f"Confidence dropped from {current_confidence:.2f} to {new_confidence:.2f}."
        )

    def evaluate_execution(
        self,
        results: List[Dict[str, Any]],
        performance_metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Produce a structured evaluation summary of the execution.

        Analyzes agent results and performance to identify successes,
        failures, and efficiency patterns for CTDE training.

        Args:
            results: Per-agent execution results.
            performance_metrics: Timing and efficiency data.

        Returns:
            Evaluation summary dict with metrics and recommendations.
        """
        total_agents = len(results)
        completed = sum(1 for r in results if r.get("status") == "completed")
        failed = sum(1 for r in results if r.get("status") == "failed")
        success_rate = completed / max(total_agents, 1)

        agent_times = performance_metrics.get("agent_times_seconds", {})
        avg_time = (
            sum(agent_times.values()) / max(len(agent_times), 1)
            if agent_times else 0
        )

        # Identify slow agents (took > 2x average)
        slow_agents = [
            name for name, t in agent_times.items()
            if t > avg_time * 2 and avg_time > 0
        ]
        
        # Identify fast agents (took < 0.5x average) 
        fast_agents = [
            name for name, t in agent_times.items()
            if t < avg_time * 0.5 and avg_time > 0
        ]

        evaluation = {
            "total_agents": total_agents,
            "completed": completed,
            "failed": failed,
            "success_rate": success_rate,
            "avg_agent_time": round(avg_time, 2),
            "total_time": performance_metrics.get("total_time_seconds", 0),
            "efficiency_gain": performance_metrics.get("efficiency_gain_seconds", 0),
            "slow_agents": slow_agents,
            "fast_agents": fast_agents,
            "recommendations": [],
        }

        # Generate recommendations
        if slow_agents:
            evaluation["recommendations"].append(
                f"[FEEDBACK] Agents {slow_agents} took too long → Consider parallel execution or task splitting"
            )
        if failed > 0:
            evaluation["recommendations"].append(
                f"[FEEDBACK] {failed} agent(s) failed → Review error handling and fallback strategies"
            )
        if success_rate == 1.0:
            evaluation["recommendations"].append(
                f"[FEEDBACK] All agents succeeded in {evaluation['total_time']}s → Workflow is stable"
            )

        self.logger.info(
            f"[FEEDBACK] Evaluation complete — {completed}/{total_agents} succeeded, "
            f"efficiency gain: {evaluation['efficiency_gain']}s"
        )

        for rec in evaluation["recommendations"]:
            self.logger.info(rec)

        return evaluation

    def send_to_ctde(self, ctde_coordinator, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Feed execution data to the CTDE coordinator for centralized training.

        Args:
            ctde_coordinator: The CTDECoordinator instance.
            execution_data: Dict with scenario, agent_configs, results,
                          performance_metrics, and dialogue_logs.

        Returns:
            CTDE training result dict.
        """
        self.logger.info("[FEEDBACK] Sending execution data to CTDE for training...")

        ctde_result = ctde_coordinator.train_from_execution(
            scenario=execution_data.get("scenario", ""),
            agent_configs=execution_data.get("agent_configs", []),
            results=execution_data.get("results", []),
            performance_metrics=execution_data.get("performance_metrics", {}),
            dialogue_logs=execution_data.get("dialogue_logs"),
        )

        self.logger.info(
            f"[FEEDBACK] CTDE training complete — "
            f"{len(ctde_result.get('policies_updated', []))} policies updated"
        )

        return ctde_result
