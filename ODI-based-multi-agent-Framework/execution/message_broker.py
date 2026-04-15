import asyncio
from typing import Dict, List, Optional
from execution.message_schema import Message
from execution.execution_logger import ExecutionLogger

class MessageBroker:
    def __init__(self, logger: ExecutionLogger):
        self.queues: Dict[str, asyncio.Queue] = {}
        self.logger = logger
        # Phase 5: Track conversation threads for multi-turn dialogue
        self.conversation_history: Dict[str, List[Message]] = {}
        
    def register_agent(self, agent_name: str):
        if agent_name not in self.queues:
            self.queues[agent_name] = asyncio.Queue()
            
    async def send_message(self, message: Message):
        if message.receiver in self.queues:
            await self.queues[message.receiver].put(message)
            self.logger.log_message(message, "SENT")
        else:
            # Drop invalid receiver silently
            pass

    async def send_dialogue_message(self, message: Message):
        """Send a message and record it in the conversation history."""
        # Store in conversation thread
        conv_id = message.conversation_id or "default"
        if conv_id not in self.conversation_history:
            self.conversation_history[conv_id] = []
        self.conversation_history[conv_id].append(message)
        
        # Also route through normal message queue
        await self.send_message(message)

    def get_conversation(self, conversation_id: str) -> List[Message]:
        """Retrieve full conversation thread by ID."""
        return self.conversation_history.get(conversation_id, [])

    async def get_messages_for(self, agent_name: str) -> List[Message]:
        messages = []
        if agent_name in self.queues:
            queue = self.queues[agent_name]
            while not queue.empty():
                msg = await queue.get()
                messages.append(msg)
                self.logger.log_message(msg, "RECEIVED")
        return messages
