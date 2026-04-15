import asyncio
import time
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from agents.base_agent import BaseAgent
from registry.agent_registry import AgentRegistry
from execution.message_broker import MessageBroker
from execution.performance_monitor import PerformanceMonitor
from execution.execution_logger import ExecutionLogger
from execution.message_schema import Message

class AsyncExecutor:
    """Core execution engine for handling parallel multi-agent execution."""
    
    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self.logger = ExecutionLogger()
        self.monitor = PerformanceMonitor()
        self.message_broker = MessageBroker(self.logger)

    def _identify_parallel_groups(self, agent_configs: List[Dict[str, Any]]) -> List[List[str]]:
        """Identify execution levels for parallel grouping using BFS on dependency graph."""
        all_agents = {cfg["name"] for cfg in agent_configs}
        graph: Dict[str, List[str]] = defaultdict(list)
        in_degree: Dict[str, int] = {name: 0 for name in all_agents}

        for cfg in agent_configs:
            agent_name = cfg["name"]
            for dep in cfg.get("dependencies", []):
                if dep in all_agents:
                    graph[dep].append(agent_name)
                    in_degree[agent_name] += 1

        levels = []
        queue = [name for name in all_agents if in_degree[name] == 0]

        while queue:
            levels.append(queue)
            self.monitor.record_parallel_group(queue)
            next_queue = []
            for node in queue:
                for neighbor in graph[node]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_queue.append(neighbor)
            queue = next_queue
            
        return levels

    async def _execute_agent_async(
        self, 
        agent: BaseAgent, 
        context: Dict[str, Any], 
        memory_context: List[str]
    ) -> Tuple[str, Dict[str, Any]]:
        self.logger.log_agent_start(agent.name)
        start_time = time.time()
        
        try:
            # Bind broker to agent
            agent.message_broker = self.message_broker
            
            # Fetch incoming messages BEFORE execution
            incoming = await self.message_broker.get_messages_for(agent.name)
            agent.incoming_messages = incoming
            
            # Run the legacy synchronous execute() method in a separate thread so we don't block
            result = await asyncio.to_thread(agent.execute, context, memory_context)
            
            # Send INFORM broadcast to dependents indicating success
            for dep in getattr(agent, "dependents", []):
                msg = Message(
                    performative="INFORM",
                    sender=agent.name,
                    receiver=dep,
                    content=f"Completed gracefully: {result.get('summary', 'Done')[:50]}..."
                )
                await self.message_broker.send_message(msg)
                
        except Exception as e:
            self.logger.log(f"[ERROR] Agent {agent.name} failed: {e}")
            result = {
                "agent": agent.name,
                "status": "failed",
                "summary": str(e)
            }
            # Send FAIL broadcast
            for dep in getattr(agent, "dependents", []):
                msg = Message(
                    performative="FAIL",
                    sender=agent.name,
                    receiver=dep,
                    content=str(e)
                )
                await self.message_broker.send_message(msg)
                
        duration = time.time() - start_time
        self.monitor.record_agent_time(agent.name, duration)
        self.logger.log_agent_end(agent.name, duration)
        
        return agent.name, result

    async def execute_agents(
        self,
        scenario_text: str,
        agent_configs: List[Dict[str, Any]],
        memory_context: List[str],
        event_callback: Any = None
    ) -> Dict[str, Any]:
        """Execute agents asynchronously ensuring strict dependency resolution."""
        self.logger.log_execution_start(scenario_text, len(agent_configs))
        self.monitor.start_execution()
        
        # Pre-process backwards dependencies mapping to easily know who to notify when finished
        dependents_map = defaultdict(list)
        for cfg in agent_configs:
            agent_name = cfg["name"]
            self.message_broker.register_agent(agent_name)
            for dep in cfg.get("dependencies", []):
                dependents_map[dep].append(agent_name)
                
        # Attach dependents list to agents in the registry
        for cfg in agent_configs:
            agent = self.registry.get_agent(cfg["name"])
            if agent:
                agent.dependents = dependents_map[cfg["name"]]
                
        levels = self._identify_parallel_groups(agent_configs)
        
        context: Dict[str, Any] = {"scenario": scenario_text}
        results: List[Dict[str, Any]] = []
        
        # Sequentially execute level by level, but PARALLEL inside the level
        for level_idx, parallel_group in enumerate(levels):
            self.logger.log_level(level_idx, parallel_group)
            
            # Notify frontend of groups executing
            if event_callback:
                for agent_name in parallel_group:
                    event_callback("agent_executing", {"agent": agent_name})
            
            tasks = []
            for agent_name in parallel_group:
                agent = self.registry.get_agent(agent_name)
                if agent:
                    tasks.append(self._execute_agent_async(agent, context, memory_context))
                    
            if tasks:
                level_results = await asyncio.gather(*tasks)
                for agent_name, result in level_results:
                    context[agent_name] = result
                    results.append(result)
                    if event_callback:
                        event_callback("agent_completed", {"result": result})
                        
        self.monitor.end_execution()
        
        # Flatten execution hierarchy to list matching original Phase 2/3 outputs
        flattened_execution_order = [n for gl in levels for n in gl]

        return {
            "scenario": scenario_text,
            "agents_created": len(agent_configs),
            "execution_order": flattened_execution_order, # Maintain backwards compatibility
            "execution_levels": levels,
            "parallel_groups": levels,
            "messages": [], # Real runtime trace happens internally via brokers and logs
            "performance_metrics": self.monitor.get_metrics(),
            "execution_logs": self.logger.get_logs(),
            "results": results
        }
