from typing import List
from execution.message_schema import Message

class ExecutionLogger:
    def __init__(self):
        self.logs: List[str] = []
        
    def log(self, message: str):
        self.logs.append(message)
        print(message)
        
    def log_execution_start(self, scenario: str, num_agents: int):
        self.log("===== EXECUTION TRACE =====")
        self.log(f"Scenario: {scenario}")
        self.log(f"Agents Created: {num_agents}")
        
    def log_level(self, level: int, agents: List[str]):
        if len(agents) > 1:
            self.log(f"[LEVEL {level}] Running agents in parallel: {agents}")
        else:
            self.log(f"[LEVEL {level}] Running agents: {agents}")
            
    def log_agent_start(self, agent_name: str):
        self.log(f"[AGENT START] {agent_name}")
        
    def log_agent_end(self, agent_name: str, duration: float):
        self.log(f"[AGENT END] {agent_name} (time: {duration:.2f}s)")
        
    def log_message(self, message: Message, action: str):
        if action == "SENT":
            self.log(f"[MESSAGE SENT] {message.sender} -> {message.receiver} | {message.performative} | \"{message.content}\"")
        elif action == "RECEIVED":
            self.log(f"[MESSAGE RECEIVED] {message.receiver} <- {message.sender}")
    
    # ── Phase 5: Dialogue Logging ──
    
    def log_dialogue_start(self, agent_a: str, agent_b: str, conv_id: str):
        self.log(f"[DIALOGUE START] {agent_a} <-> {agent_b} (conv={conv_id})")
    
    def log_dialogue_turn(self, turn: int, sender: str, receiver: str, performative: str):
        self.log(f"[TURN {turn}] {sender} -> {receiver} ({performative})")
    
    def log_dialogue_end(self, conv_id: str, turns: int):
        self.log(f"[DIALOGUE END] Converged in {turns} turns (conv={conv_id})")
    
    # ── Phase 5: CTDE Logging ──
    
    def log_ctde_update(self, agent_role: str, action: str = "updated"):
        self.log(f"[CTDE TRAINING] {action.capitalize()} shared policy for: {agent_role}")
    
    def log_ctde_policy(self, agent_role: str, practices: int, failures: int):
        self.log(f"[CTDE POLICY] Providing hints for {agent_role} ({practices} practices, {failures} failures)")
    
    # ── Phase 5: Learning Logging ──
    
    def log_learning_insight(self, insight_summary: str):
        self.log(f"[LEARNING] {insight_summary}")
            
    def get_logs(self) -> List[str]:
        return self.logs
