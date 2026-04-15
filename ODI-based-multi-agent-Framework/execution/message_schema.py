from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import time

@dataclass
class Message:
    performative: str  # e.g., REQUEST, INFORM, CONFIRM, FAIL
    sender: str
    receiver: str
    content: str
    timestamp: float = None
    conversation_id: Optional[str] = None  # Phase 5: Multi-turn dialogue thread ID
    turn_number: Optional[int] = None      # Phase 5: Turn number within dialogue
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
            
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "performative": self.performative,
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "timestamp": self.timestamp,
        }
        if self.conversation_id:
            result["conversation_id"] = self.conversation_id
        if self.turn_number is not None:
            result["turn_number"] = self.turn_number
        return result
