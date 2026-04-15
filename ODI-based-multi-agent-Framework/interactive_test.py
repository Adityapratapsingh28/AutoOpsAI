"""
Interactive Phase 5 Terminal Test
──────────────────────────────────
Run: python interactive_test.py
Type a scenario, press Enter, and watch every pipeline step execute live.
Type 'exit' to quit.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from orchestrator.meta_orchestrator import MetaOrchestrator


# ── Pretty Printing Helpers ──

BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
PURPLE = "\033[95m"
CYAN = "\033[96m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def divider(title, color=BLUE):
    print(f"\n{color}{'━'*70}")
    print(f"  {BOLD}{title}{RESET}")
    print(f"{color}{'━'*70}{RESET}\n")


def step_header(num, title, color=CYAN):
    print(f"\n{color}{BOLD}  ▸ STEP {num} — {title}{RESET}")
    print(f"{DIM}  {'─'*60}{RESET}")


def print_result(result: dict):
    """Print the full Phase 5 orchestration result."""

    perf = result.get("performance_metrics", {})
    agents_created = result.get("agents_created", 0)
    exec_order = result.get("execution_order", [])
    results = result.get("results", [])

    # ── Step 1-2: Memory + Scenario Analysis ──
    step_header(1, "MEMORY RETRIEVAL & SCENARIO ANALYSIS")
    mem = result.get("memory_context", [])
    if mem:
        for m in mem:
            scenario_match = m.split("Scenario:")
            title = scenario_match[1].split("\n")[0].strip() if len(scenario_match) > 1 else "Past execution"
            print(f"    {GREEN}✓{RESET} Retrieved: \"{title}\"")
    else:
        print(f"    {DIM}No past executions found — fresh workflow generated{RESET}")

    # ── Step 3-4: Agent Creation ──
    step_header(3, f"AGENT SYNTHESIS ({agents_created} agents)")
    for name in exec_order:
        print(f"    {PURPLE}◉{RESET} {name}")

    # ── Step 5: Execution Results ──
    step_header(5, "AGENT EXECUTION RESULTS")
    for r in results:
        status_icon = f"{GREEN}✔{RESET}" if r.get("status") == "completed" else f"{RED}✘{RESET}"
        print(f"    {status_icon} {BOLD}{r.get('agent', '??')}{RESET}")
        print(f"      {DIM}{r.get('summary', 'No summary')[:120]}{RESET}")

    # ── Step 6: Multi-Turn Dialogues ──
    dialogues = result.get("dialogue_logs", [])
    step_header(6, f"MULTI-TURN DIALOGUES ({len(dialogues)} conversations)")
    if dialogues:
        for dlg in dialogues:
            agents_label = dlg.get("agents", "??")
            turns = dlg.get("turns", 0)
            status = dlg.get("status", "unknown")
            status_label = f"{GREEN}converged{RESET}" if status == "converged" else f"{YELLOW}{turns} turns{RESET}"
            print(f"    {BLUE}💬{RESET} {BOLD}{agents_label}{RESET}  [{status_label}]")
            for turn in dlg.get("turn_details", []):
                perf_color = CYAN if turn["performative"] == "REQUEST" else GREEN if turn["performative"] == "INFORM" else YELLOW
                print(f"       {perf_color}[{turn['performative']}]{RESET} {turn['sender']} → {turn['receiver']}")
                print(f"         {DIM}\"{turn['content'][:100]}...\"{RESET}")
    else:
        print(f"    {DIM}No dialogues triggered (no dependent agent pairs){RESET}")

    # ── Step 7: Feedback Evaluation ──
    feedback = result.get("feedback_evaluation", {})
    step_header(7, "FEEDBACK EVALUATION")
    success_rate = feedback.get("success_rate", 0)
    sr_color = GREEN if success_rate >= 0.8 else YELLOW if success_rate >= 0.5 else RED
    print(f"    Success Rate:    {sr_color}{BOLD}{success_rate:.0%}{RESET}")
    print(f"    Completed:       {feedback.get('completed', 0)}/{feedback.get('total_agents', 0)}")
    print(f"    Total Time:      {feedback.get('total_time', 0)}s")
    print(f"    Efficiency Gain: {GREEN}{feedback.get('efficiency_gain', 0)}s{RESET}")
    slow = feedback.get("slow_agents", [])
    if slow:
        print(f"    Slow Agents:     {RED}{', '.join(slow)}{RESET}")
    for rec in feedback.get("recommendations", []):
        print(f"    {YELLOW}→ {rec}{RESET}")

    # ── Step 8: CTDE Training ──
    ctde = result.get("ctde_updates", [])
    step_header(8, f"CTDE CENTRALIZED TRAINING ({len(ctde)} policies)")
    for update in ctde:
        print(f"    {PURPLE}⬡{RESET} {update.get('agent', '??')} ({update.get('role', '')}) — {GREEN}{update.get('policy_action', 'updated')}{RESET}")

    # ── Step 9: Learning Summary ──
    learning = result.get("learning_summary", {})
    step_header(9, "LEARNING STORE SUMMARY")
    print(f"    Policies Updated:    {learning.get('policies_updated', 0)}")
    print(f"    Total Policies:      {learning.get('total_stored_policies', 0)}")
    print(f"    Total Insights:      {learning.get('total_stored_insights', 0)}")

    # ── Performance Summary ──
    divider("PERFORMANCE SUMMARY", GREEN)
    print(f"    Total Execution Time:  {BOLD}{perf.get('total_time_seconds', 0)}s{RESET}")
    print(f"    Efficiency Gain:       {GREEN}{BOLD}{perf.get('efficiency_gain_seconds', 0)}s{RESET}")
    print(f"    Sequential Estimate:   {perf.get('sequential_estimate_seconds', 0)}s")
    print(f"    Agents:                {agents_created}")
    print(f"    Dialogues:             {len(dialogues)}")
    print(f"    CTDE Updates:          {len(ctde)}")


def main():
    divider("MULTI-AGENT ORCHESTRATION — INTERACTIVE TEST (Phase 5)", PURPLE)
    print(f"  {DIM}Type a scenario and press Enter to execute the full pipeline.")
    print(f"  Type 'exit' to quit.{RESET}\n")

    orchestrator = MetaOrchestrator()

    run_count = 0
    while True:
        try:
            scenario = input(f"\n{BOLD}{CYAN}SCENARIO ▸ {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not scenario or scenario.lower() == "exit":
            print(f"\n{DIM}Goodbye!{RESET}\n")
            break

        run_count += 1
        divider(f"RUN {run_count}", BLUE)
        print(f"  {DIM}Scenario: {scenario}{RESET}")

        try:
            result = orchestrator.execute(scenario)
            print_result(result)
            divider(f"RUN {run_count} COMPLETE ✅", GREEN)
        except Exception as e:
            print(f"\n  {RED}ERROR: {e}{RESET}\n")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
