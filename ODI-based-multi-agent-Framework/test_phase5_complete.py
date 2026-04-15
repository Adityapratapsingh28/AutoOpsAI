"""
Phase 5 Complete Test — CTDE + Multi-Turn Dialogue + Learning Store.

Tests the full Phase 5 pipeline:
  Run 1: Fresh workflow generation with CTDE initial training
  Run 2: Workflow reuse with policy hints + dialogue + learning

Expected logs:
  - [CTDE TRAINING] policy updates
  - [DIALOGUE START/TURN/END] conversation traces
  - [FEEDBACK] evaluation results
  - [LEARNING STORE] insights saved
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from orchestrator.meta_orchestrator import MetaOrchestrator


def print_divider(title: str):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def print_result(run_label: str, result: dict):
    print_divider(f"{run_label} — EXECUTION SUMMARY")
    
    perf = result.get("performance_metrics", {})
    print(f"  Agents Created:     {result.get('agents_created')}")
    print(f"  Execution Order:    {result.get('execution_order')}")
    print(f"  Total Time:         {perf.get('total_time_seconds')}s")
    print(f"  Efficiency Gain:    {perf.get('efficiency_gain_seconds')}s")
    
    # Phase 5: CTDE Updates
    ctde_updates = result.get("ctde_updates", [])
    print(f"\n  CTDE Policies Updated: {len(ctde_updates)}")
    for update in ctde_updates:
        print(f"    → {update.get('agent')} ({update.get('role')}): {update.get('policy_action')}")
    
    # Phase 5: Dialogue Logs
    dialogue_logs = result.get("dialogue_logs", [])
    print(f"\n  Multi-Turn Dialogues: {len(dialogue_logs)}")
    for dlg in dialogue_logs:
        print(f"    → {dlg.get('agents')}: {dlg.get('turns')} turns ({dlg.get('status')})")
        for turn in dlg.get("turn_details", []):
            print(f"      [Turn {turn['turn']}] {turn['sender']} → {turn['receiver']} ({turn['performative']})")
            print(f"        \"{turn['content'][:100]}...\"")
    
    # Phase 5: Learning Summary
    learning = result.get("learning_summary", {})
    print(f"\n  Learning Summary:")
    print(f"    Policies Updated:    {learning.get('policies_updated')}")
    print(f"    Total Policies:      {learning.get('total_stored_policies')}")
    print(f"    Total Insights:      {learning.get('total_stored_insights')}")
    
    # Phase 5: Feedback Evaluation
    feedback = result.get("feedback_evaluation", {})
    print(f"\n  Feedback Evaluation:")
    print(f"    Success Rate:        {feedback.get('success_rate', 0):.0%}")
    print(f"    Completed:           {feedback.get('completed')}/{feedback.get('total_agents')}")
    print(f"    Slow Agents:         {feedback.get('slow_agents', [])}")
    for rec in feedback.get("recommendations", []):
        print(f"    → {rec}")


def main():
    orchestrator = MetaOrchestrator()
    
    # ── RUN 1: Fresh scenario — generates new workflow ──
    scenario_1 = (
        "A massive fire broke out in the downtown library. "
        "50 people are trapped inside and the oxygen is running low."
    )
    
    print_divider("PHASE 5 TEST — RUN 1 (Expected: GENERATE FRESH WORKFLOW)")
    print(f"  Scenario: {scenario_1}\n")
    result_1 = orchestrator.execute(scenario_1)
    print_result("RUN 1", result_1)
    
    # ── RUN 2: Similar scenario — should REUSE + ADAPT + DIALOGUE ──
    scenario_2 = (
        "A huge fire just started at the national archives building. "
        "120 people are trapped and the roof is collapsing."
    )
    
    print_divider("PHASE 5 TEST — RUN 2 (Expected: REUSE & ADAPT WORKFLOW)")
    print(f"  Scenario: {scenario_2}\n")
    result_2 = orchestrator.execute(scenario_2)
    print_result("RUN 2", result_2)
    
    # ── VERIFICATION ──
    print_divider("VERIFICATION")
    
    # Check CTDE policies were stored
    all_policies = orchestrator.learning_store.get_all_policies()
    print(f"  ✓ CTDE Policies stored: {len(all_policies)} roles")
    for role in all_policies:
        p = all_policies[role]
        print(f"    → {role}: {len(p.get('best_practices',[]))} practices, "
              f"{len(p.get('common_failures',[]))} failures, "
              f"{len(p.get('optimal_patterns',[]))} patterns")
    
    # Check learning insights
    insights = orchestrator.learning_store.get_insights()
    print(f"\n  ✓ Learning Insights stored: {len(insights)}")
    for i, insight in enumerate(insights):
        print(f"    → Insight {i+1}: success_rate={insight.get('success_rate', 0):.0%}, "
              f"time={insight.get('total_time', 0)}s, "
              f"dialogues={insight.get('dialogue_count', 0)}")
    
    # Check dialogue happened in run 2
    dlg_2 = result_2.get("dialogue_logs", [])
    if dlg_2:
        print(f"\n  ✅ Multi-turn dialogue executed in Run 2: {len(dlg_2)} conversation(s)")
    else:
        print(f"\n  ⚠️  No dialogues in Run 2 (agents may not have had dependency pairs)")
    
    # Check graph topology
    agents_1 = set(result_1.get('execution_order', []))
    agents_2 = set(result_2.get('execution_order', []))
    if len(agents_1) == len(agents_2):
        print(f"  ✅ Graph topology preserved (both runs: {len(agents_1)} agents)")
    else:
        print(f"  ⚠️  Graph topology changed ({len(agents_1)} vs {len(agents_2)} agents)")
    
    print_divider("PHASE 5 TEST COMPLETE ✅")


if __name__ == "__main__":
    main()
