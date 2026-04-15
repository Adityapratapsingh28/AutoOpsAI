import sys
import os
from pathlib import Path

# Add the project root to the Python path dynamically so Python and Pylance can resolve local modules (like 'orchestrator')
project_root = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root))

from orchestrator.meta_orchestrator import MetaOrchestrator
import time

def print_structured_output(scenario, result):
    print("\n" + "="*80)
    print(" 📋 EXECUTION SUMMARY ")
    print("="*80)
    
    # 1. Summary Metrics
    perf = result.get('performance_metrics', {})
    eff_gain = perf.get('efficiency_gain_seconds', 0)
    total_time = perf.get('total_time_seconds', 'N/A')
    
    print(f"[{'Metric':<25}] | [{'Value':<50}]")
    print(f"-"*80)
    print(f" {'Scenario':<25} | {scenario[:48]}{'...' if len(scenario)>48 else ''}")
    print(f" {'Agents Created':<25} | {result.get('agents_created')}")
    print(f" {'Total Parallel Time':<25} | {total_time}s (Efficiency Gain: {eff_gain}s)")
    print(f" {'Execution Trace ID':<25} | {result.get('execution_id', 'Unsaved')}")
    print()

    # 2. Execution Levels
    print("\n" + "="*80)
    print(" ��️ TOPOLOGICAL EXECUTION ORDER ")
    print("="*80)
    print(f"[{'Lvl':<3}] | [{'Agent Name':<25}] | [{'Dependencies':<35}]")
    print(f"-"*80)
    
    graph = result.get('graph', {})
    for agent_name in result.get('execution_order', []):
        node = graph.get(agent_name, {})
        lvl = node.get('level', 0)
        dep = ", ".join(node.get('dependencies', [])) if node.get('dependencies') else "None (Root)"
        print(f" {lvl:<3}  |  {agent_name:<25} |  {dep[:35]}...")
        
    # 3. Reasoning Trace
    print("\n" + "="*80)
    print(" 🧠 AGENT REASONING & ACTIONS ")
    print("="*80)
    
    outputs = result.get('agent_outputs', {})
    for agent_name, output in outputs.items():
        summary = output.get('summary', 'Executed tasks.')
        print(f"► {agent_name.upper()}:")
        print(f"  {summary}")
        print()


def main():
    try:
        orchestrator = MetaOrchestrator()
        
        print("\n" + "#"*80)
        print("    PHASE 5: ADAPTIVE ORCHESTRATOR TERMINAL TESTER    ")
        print("#"*80)
        
        while True:
            # 1. Get user input from the terminal interactively
            scenario = input("\nScenario (or 'exit' to quit): ")
            if scenario.lower() == 'exit':
                break
                
            print(f"\n[ORCHESTRATOR START] Processing incoming scenario constraints...\n")
            
            # 2. Run the adaptive orchestrator
            result = orchestrator.execute(scenario)
            
            # 3. Pretty print everything!
            print_structured_output(scenario, result)
            
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    main()
