import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from orchestrator.meta_orchestrator import MetaOrchestrator

def main():
    scenario = "A massive 8.0 earthquake just hit San Francisco. The main hospital has lost power and the backup generators are failing. There are 200 patients in critical condition, and the roads are blocked by debris."
    
    print(f"Testing scenario: {scenario}")
    
    # Initialize orchestrator
    orchestrator = MetaOrchestrator()
    
    try:
        # Run execution
        result = orchestrator.execute(scenario)
        print("\n=== EXECUTION SUCCESS ===")
        print(f"Agents created: {result.get('agents_created')}")
        print(f"Execution Order (Flattened): {result.get('execution_order')}")
        print(f"Execution Levels: {result.get('execution_levels')}")
        
        perf = result.get('performance_metrics', {})
        print("\n=== PERFORMANCE METRICS ===")
        print(f"Total Time: {perf.get('total_time_seconds')}s")
        print(f"Sequential Estimate: {perf.get('sequential_estimate_seconds')}s")
        print(f"Efficiency Gain: {perf.get('efficiency_gain_seconds')}s")
        print(f"Parallel Groups: {perf.get('parallel_groups')}")
        print(f"Agent Times: {perf.get('agent_times_seconds')}")
        
        print("\n=== EXECUTION LOGS ===")
        for log in result.get('execution_logs', []):
            print(log)
            
    except Exception as e:
        print(f"\n=== EXECUTION FAILED ===")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
