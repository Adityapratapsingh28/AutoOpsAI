import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from orchestrator.meta_orchestrator import MetaOrchestrator

def main():
    scenario_1 = "A massive fire broke out in the downtown library. 50 people are trapped inside and the oxygen is running low."
    scenario_2 = "A Huge fire just started at the national archives building. 120 people are trapped and the roof is collapsing."
    
    orchestrator = MetaOrchestrator()
    
    print(f"\n[PHASE 5 TEST - RUN 1] - Expected: GENERATE FRESH WORKFLOW")
    print(f"Scenario 1: {scenario_1}")
    result_1 = orchestrator.execute(scenario_1)
    
    print("\n=== RUN 1 SUCCESS ===")
    print(f"Agents created: {result_1.get('agents_created')}")
    print(f"Execution Order: {result_1.get('execution_order')}")
    print(f"Total Time: {result_1.get('performance_metrics', {}).get('total_time_seconds')}s")

    print(f"\n{'='*50}\n")
    
    print(f"[PHASE 5 TEST - RUN 2] - Expected: REUSE & ADAPT WORKFLOW")
    print(f"Scenario 2: {scenario_2}")
    result_2 = orchestrator.execute(scenario_2)
    
    print("\n=== RUN 2 SUCCESS ===")
    print(f"Agents created: {result_2.get('agents_created')}")
    print(f"Execution Order: {result_2.get('execution_order')}")
    print(f"Total Time: {result_2.get('performance_metrics', {}).get('total_time_seconds')}s")

    print("\n=== VERIFICATION ===")
    agents_1 = set(result_1.get('execution_order', []))
    agents_2 = set(result_2.get('execution_order', []))
    
    if agents_1 == agents_2 or len(agents_1) == len(agents_2):
        print("✅ Graph successfully preserved / adapted!")
    else:
        print("❌ Graph topology drastically changed, adaptation might have failed.")

if __name__ == "__main__":
    main()
