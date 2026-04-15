from typing import Dict, List, Any
import time

class PerformanceMonitor:
    def __init__(self):
        self.start_time: float = 0
        self.end_time: float = 0
        self.agent_times: Dict[str, float] = {}
        self.parallel_groups: List[List[str]] = []
        
    def start_execution(self):
        self.start_time = time.time()
        
    def end_execution(self):
        self.end_time = time.time()
        
    def record_agent_time(self, agent_name: str, duration: float):
        self.agent_times[agent_name] = duration
        
    def record_parallel_group(self, agents: List[str]):
        self.parallel_groups.append(agents)
        
    def get_metrics(self) -> Dict[str, Any]:
        total_time = self.end_time - self.start_time
        sum_sequential_time = sum(self.agent_times.values()) if self.agent_times else 0
        efficiency_gain = max(0.0, sum_sequential_time - total_time)
        
        return {
            "total_time_seconds": round(total_time, 2),
            "agent_times_seconds": {k: round(v, 2) for k, v in self.agent_times.items()},
            "parallel_groups": self.parallel_groups,
            "sequential_estimate_seconds": round(sum_sequential_time, 2),
            "efficiency_gain_seconds": round(efficiency_gain, 2)
        }
