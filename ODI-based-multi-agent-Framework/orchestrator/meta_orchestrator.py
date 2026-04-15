"""
Meta-Orchestrator for the Multi-Agent Orchestration Framework.

The Meta-Orchestrator is the central coordination entity that implements
the full memory-augmented dynamic agent synthesis pipeline:

  1. Receive scenario description
  2. Retrieve memory context from past executions
  3. Adaptive scenario analysis (REUSE or GENERATE)
  4. CTDE provides shared policy hints
  5. Create agents dynamically (with policy injection)
  6. Resolve execution order via AsyncExecutor
  7. Run multi-turn dialogues between dependent agents
  8. Feedback loop evaluation
  9. CTDE centralized training update
  10. Save execution trace + learning insights
"""

from typing import Any, Dict, List

from dependency.dependency_resolver import DependencyResolver
from factory.agent_factory import create_agent
from llm.llm_service import LLMService
from memory.memory_manager import MemoryManager
from registry.agent_registry import AgentRegistry
from utils.logger import setup_logger
from execution.async_executor import AsyncExecutor
import asyncio


class MetaOrchestrator:
    """Central orchestrator that coordinates memory-augmented multi-agent execution.

    Implements the complete Phase 5 pipeline: memory retrieval, adaptive workflow
    reuse, CTDE policy injection, LLM-driven scenario analysis, runtime agent
    synthesis, dependency-ordered execution with multi-turn dialogue,
    feedback evaluation, centralized training, and learning store persistence.
    """

    def __init__(self) -> None:
        """Initialize the Meta-Orchestrator and all subsystems."""
        self.logger = setup_logger("MetaOrchestrator")
        self.llm_service = LLMService()
        self.registry = AgentRegistry()
        self.dependency_resolver = DependencyResolver()
        self.memory_manager = MemoryManager()
        
        # Phase 5 — Adaptation Layer (existing)
        from adaptation.retrieval_engine import RetrievalEngine
        from adaptation.workflow_adapter import WorkflowAdapter
        from adaptation.feedback_loop import FeedbackLoop
        self.retrieval_engine = RetrievalEngine(self.memory_manager.vector_store)
        self.workflow_adapter = WorkflowAdapter(self.llm_service)
        self.feedback_loop = FeedbackLoop(self.memory_manager.vector_store)
        
        # Phase 5 — NEW: CTDE, Dialogue, Learning Store
        from adaptation.learning_store import LearningStore
        from adaptation.ctde_coordinator import CTDECoordinator
        from adaptation.dialogue_manager import DialogueManager
        self.learning_store = LearningStore()
        self.ctde_coordinator = CTDECoordinator(self.learning_store)
        self.dialogue_manager = DialogueManager(max_turns=3)
        
        self.logger.info("Meta-Orchestrator initialized (Phase 5 — Full Adaptive + CTDE).")

    def execute(
        self, scenario_text: str, event_callback: Any = None
    ) -> Dict[str, Any]:
        """Run the full Phase 5 orchestration pipeline.

        Args:
            scenario_text: A natural-language scenario description.
            event_callback: Optional callable to emit real-time events.

        Returns:
            A dictionary containing the scenario, agents created,
            execution order, memory context, dialogue logs, CTDE updates,
            learning summary, and per-agent results.
        """
        self.logger.info(f"Scenario received: {scenario_text}")
        if event_callback:
            event_callback("status", {"step": "Initializing pipeline..."})

        # ── Step 1: Retrieve memory context ──
        self.logger.info("Step 1 — Retrieving memory context...")
        if event_callback:
            event_callback("status", {"step": "Retrieving memory context..."})
        memory_context: List[str] = self.memory_manager.retrieve_context(
            scenario_text
        )
        self.memory_manager.init_session(scenario_text)
        if event_callback:
            event_callback("memory_retrieved", {"context": memory_context})

        # ── Step 2: Adaptive Scenario Analysis (REUSE or GENERATE) ──
        self.logger.info("Step 2 — Checking for reusable past workflows...")
        eval_result = self.retrieval_engine.evaluate_scenario(scenario_text)
        
        reused_experience_id = None
        past_metadata = {}
        
        if eval_result["action"] == "REUSE":
            self.logger.info("Reusing and adapting past workflow...")
            if event_callback:
                event_callback("status", {"step": "Adapting past workflow..."})
                
            past_experience = eval_result["experience"]
            past_metadata = past_experience.get("metadata", {})
            past_scenario = past_metadata.get("scenario", "")
            
            import json
            try:
                past_agent_configs = json.loads(past_metadata.get("workflow_graph", "[]"))
            except json.JSONDecodeError:
                past_agent_configs = []
            
            # Phase 5: Get CTDE policy hints for adaptation
            all_policies = self.learning_store.get_all_policies()
            
            agent_configs = self.workflow_adapter.adapt_workflow(
                past_agent_configs, past_scenario, scenario_text,
                policy_hints=all_policies if all_policies else None,
            )
            reused_experience_id = past_experience.get("id")
        else:
            self.logger.info("Generating fresh workflow...")
            if event_callback:
                event_callback("status", {"step": "Generating fresh workflow..."})
            agent_configs: List[Dict[str, Any]] = self.llm_service.analyze_scenario(
                scenario_text
            )
            
        if event_callback:
            event_callback("agents_designed", {"agents": agent_configs})

        # ── Step 3: CTDE — Inject policy hints into agents before creation ──
        self.logger.info("Step 3 — Injecting CTDE policy hints into agents...")
        if event_callback:
            event_callback("status", {"step": "Applying CTDE policy hints..."})
            
        agent_policies = {}
        for config in agent_configs:
            role = config.get("role", config.get("name", ""))
            policy = self.ctde_coordinator.get_shared_policy(role)
            agent_policies[config["name"]] = policy

        # ── Step 4: Create agents via AgentFactory (with policy injection) ──
        self.logger.info("Step 4 — Creating agents dynamically...")
        if event_callback:
            event_callback("status", {"step": "Creating agents..."})
        for config in agent_configs:
            agent = create_agent(config)
            # Inject CTDE policy hints into agent
            agent.policy_hints = agent_policies.get(config["name"], {})
            self.registry.register_agent(agent)

        # ── Step 5: Execute agents using AsyncExecutor ──
        self.logger.info("Step 5 — Executing agents using AsyncExecutor...")
        if event_callback:
            event_callback("status", {"step": "Executing agents asynchronously..."})
            
        async_executor = AsyncExecutor(self.registry)
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            response = asyncio.run_coroutine_threadsafe(
                async_executor.execute_agents(scenario_text, agent_configs, memory_context, event_callback), 
                loop
            ).result()
        else:
            response = loop.run_until_complete(
                async_executor.execute_agents(scenario_text, agent_configs, memory_context, event_callback)
            )

        results = response["results"]
        
        # Feed results into short-term memory
        for result in results:
            self.memory_manager.short_term.store_agent_output(result.get("agent", ""), result)

        # ── Step 6: Multi-Turn Dialogue between dependent agents ──
        self.logger.info("Step 6 — Running multi-turn dialogues...")
        if event_callback:
            event_callback("status", {"step": "Running multi-turn agent dialogues..."})
            
        # Build results lookup for dialogue identification
        results_lookup = {}
        for r in results:
            results_lookup[r.get("agent", "")] = r
            
        dialogue_pairs = self.dialogue_manager.identify_dialogue_pairs(
            agent_configs, results_lookup
        )
        
        # Run dialogues for identified pairs (limit to 2 pairs to keep it efficient)
        for agent_a, agent_b, topic in dialogue_pairs[:2]:
            summary_a = results_lookup.get(agent_a, {}).get("summary", "")
            summary_b = results_lookup.get(agent_b, {}).get("summary", "")
            
            conv_id = self.dialogue_manager.start_dialogue(
                agent_a, agent_b, topic,
                agent_a_summary=summary_a,
                agent_b_summary=summary_b,
            )
            
            self.dialogue_manager.run_dialogue(conv_id, self.llm_service)
        
        dialogue_logs = self.dialogue_manager.get_dialogue_logs()
        
        # Emit dialogue logs to frontend
        if event_callback:
            event_callback("dialogue_completed", {"dialogues": dialogue_logs})

        # ── Step 7: Feedback Loop Evaluation ──
        self.logger.info("Step 7 — Running feedback evaluation...")
        if event_callback:
            event_callback("status", {"step": "Evaluating execution performance..."})
            
        perf = response.get("performance_metrics", {})
        evaluation = self.feedback_loop.evaluate_execution(results, perf)
        
        # Determine overall outcome
        outcome = "failure" if any(r.get("status") == "failed" for r in results) else "success"
        
        # Emit feedback evaluation to frontend
        if event_callback:
            event_callback("feedback_evaluated", {"evaluation": evaluation})
        
        # Penalize if a reused workflow failed
        if outcome == "failure" and reused_experience_id:
            self.logger.warning("Reused workflow failed. Triggering feedback loop penalty.")
            self.feedback_loop.penalize_experience(reused_experience_id, past_metadata)

        # ── Step 8: CTDE Centralized Training ──
        self.logger.info("Step 8 — CTDE centralized training...")
        if event_callback:
            event_callback("status", {"step": "CTDE centralized training update..."})
            
        ctde_result = self.feedback_loop.send_to_ctde(
            self.ctde_coordinator,
            {
                "scenario": scenario_text,
                "agent_configs": agent_configs,
                "results": results,
                "performance_metrics": perf,
                "dialogue_logs": dialogue_logs,
            }
        )

        # Emit CTDE training result to frontend
        if event_callback:
            event_callback("ctde_trained", {
                "policies_updated": ctde_result.get("policies_updated", []),
                "insight": ctde_result.get("insight", {}),
            })

        # ── Step 9: Save execution trace + learning insights ──
        self.logger.info("Step 9 — Saving execution trace and learning insights...")
        if event_callback:
            event_callback("status", {"step": "Saving execution trace..."})
            
        flat_order = response.get("execution_order", [])
        
        self.memory_manager.save_execution_trace(
            scenario=scenario_text,
            agents=flat_order,
            agent_configs=agent_configs,
            results=results,
            outcome=outcome,
            performance_metrics=perf,
        )

        # Build learning summary
        learning_summary = {
            "policies_updated": len(ctde_result.get("policies_updated", [])),
            "insight": ctde_result.get("insight", {}),
            "evaluation": evaluation,
            "total_stored_policies": len(self.learning_store.get_all_policies()),
            "total_stored_insights": len(self.learning_store.get_insights()),
        }

        self.logger.info(
            f"Orchestration complete — Time: {perf.get('total_time_seconds', 0)}s, "
            f"Efficiency Gain: {perf.get('efficiency_gain_seconds', 0)}s, "
            f"Dialogues: {len(dialogue_logs)}, "
            f"CTDE Updates: {len(ctde_result.get('policies_updated', []))}."
        )
        
        if event_callback:
            event_callback("dependency_resolved", {"order": flat_order})
            event_callback("orchestration_completed", response)

        # ── Build enriched final output ──
        response["dialogue_logs"] = dialogue_logs
        response["ctde_updates"] = ctde_result.get("policies_updated", [])
        response["learning_summary"] = learning_summary
        response["feedback_evaluation"] = evaluation
            
        return response
