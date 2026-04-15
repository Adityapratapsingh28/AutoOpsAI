"""
Dialogue Manager — Multi-Turn Agent Communication Controller.

Manages iterative conversations between agents in the multi-agent system.
Instead of single-shot responses, agents can engage in multi-turn dialogues
to collaboratively refine decisions, share information, and converge on
optimal solutions.

Dialogue Flow:
  Agent A → REQUEST → Agent B
  Agent B → INFORM  → Agent A
  Agent A → REQUEST (refinement)
  Agent B → CONFIRM
  Stop: Max turns reached OR convergence achieved.
"""

import uuid
import time
from typing import Any, Dict, List, Optional, Tuple
from utils.logger import setup_logger
from execution.message_schema import Message


class DialogueManager:
    """Controls multi-turn dialogues between agent pairs.

    Manages conversation threads with unique IDs, tracks dialogue
    history, determines convergence, and coordinates turn-taking
    via the message broker.

    Attributes:
        max_turns: Maximum dialogue turns before forced convergence.
        conversations: Dict of conversation_id → dialogue history.
    """

    def __init__(self, max_turns: int = 3) -> None:
        """Initialize the dialogue manager.

        Args:
            max_turns: Maximum number of turns per dialogue (default: 3).
        """
        self.logger = setup_logger("DialogueManager")
        self.max_turns = max_turns
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}
        self.logger.info(f"Dialogue Manager initialized (max_turns={max_turns}).")

    def identify_dialogue_pairs(
        self,
        agent_configs: List[Dict[str, Any]],
        results: Dict[str, Any],
    ) -> List[Tuple[str, str, str]]:
        """Identify pairs of agents that should engage in multi-turn dialogue.

        Agents with direct dependencies benefit from dialogue to refine
        their coordinated outputs. A dialogue is triggered when:
        - Agent B depends on Agent A (direct edge in DAG)
        - Both agents have completed their initial execution

        Args:
            agent_configs: The agent configuration list with dependencies.
            results: Current execution results context.

        Returns:
            List of (agent_a, agent_b, topic) tuples for dialogue.
        """
        pairs = []
        completed_agents = set(results.keys()) if isinstance(results, dict) else set()

        for config in agent_configs:
            agent_name = config.get("name", "")
            deps = config.get("dependencies", [])

            for dep in deps:
                if dep in completed_agents and agent_name in completed_agents:
                    topic = (
                        f"Coordination between {dep} and {agent_name}: "
                        f"refining shared execution strategy"
                    )
                    pairs.append((dep, agent_name, topic))

        if pairs:
            self.logger.info(f"Identified {len(pairs)} dialogue pair(s) for refinement.")
        return pairs

    def start_dialogue(
        self,
        agent_a_name: str,
        agent_b_name: str,
        topic: str,
        agent_a_summary: str = "",
        agent_b_summary: str = "",
    ) -> str:
        """Initialize a new dialogue thread between two agents.

        Args:
            agent_a_name: Name of the initiating agent.
            agent_b_name: Name of the responding agent.
            topic: The dialogue topic/goal.
            agent_a_summary: Agent A's execution summary for context.
            agent_b_summary: Agent B's execution summary for context.

        Returns:
            The unique conversation_id for this dialogue.
        """
        conversation_id = str(uuid.uuid4())[:8]

        self.conversations[conversation_id] = {
            "id": conversation_id,
            "agent_a": agent_a_name,
            "agent_b": agent_b_name,
            "topic": topic,
            "turns": [],
            "started_at": time.time(),
            "status": "active",
            "agent_a_context": agent_a_summary,
            "agent_b_context": agent_b_summary,
        }

        self.logger.info(
            f"[DIALOGUE START] {agent_a_name} ↔ {agent_b_name} "
            f"(conv={conversation_id}, topic: {topic[:60]}...)"
        )

        return conversation_id

    def run_dialogue(
        self,
        conversation_id: str,
        llm_service: Any,
    ) -> List[Dict[str, Any]]:
        """Execute the full multi-turn dialogue using LLM reasoning.

        Alternates between agents, each responding to the other's
        previous message, until convergence or max turns reached.

        Args:
            conversation_id: The dialogue thread ID.
            llm_service: LLM service instance for generating responses.

        Returns:
            List of turn records with sender, receiver, content, performative.
        """
        conv = self.conversations.get(conversation_id)
        if not conv:
            self.logger.error(f"Conversation {conversation_id} not found.")
            return []

        agent_a = conv["agent_a"]
        agent_b = conv["agent_b"]
        topic = conv["topic"]
        turns = conv["turns"]

        # Turn alternation: A starts with REQUEST, B responds with INFORM, etc.
        performative_sequence = ["REQUEST", "INFORM", "REQUEST", "CONFIRM"]

        for turn_num in range(1, self.max_turns + 1):
            # Determine sender/receiver for this turn
            if turn_num % 2 == 1:
                sender, receiver = agent_a, agent_b
            else:
                sender, receiver = agent_b, agent_a

            performative = performative_sequence[
                min(turn_num - 1, len(performative_sequence) - 1)
            ]

            # Build dialogue prompt for LLM
            history_text = ""
            if turns:
                history_text = "\n".join(
                    f"  Turn {t['turn']}: {t['sender']} → {t['receiver']} "
                    f"[{t['performative']}]: {t['content'][:100]}"
                    for t in turns
                )

            prompt = f"""You are agent '{sender}' in a multi-turn dialogue with '{receiver}'.

Topic: {topic}

Context from {agent_a}: {conv.get('agent_a_context', 'No context')[:200]}
Context from {agent_b}: {conv.get('agent_b_context', 'No context')[:200]}

Previous dialogue:
{history_text if history_text else '(Starting new dialogue)'}

You are sending a {performative} message (turn {turn_num}/{self.max_turns}).
{'Initiate the discussion about coordination.' if turn_num == 1 else 'Respond to the previous message and refine the plan.'}
{'This is your final turn — provide a conclusive summary.' if turn_num == self.max_turns else ''}

Respond with a concise, actionable message (2-3 sentences max). No JSON, just plain text."""

            try:
                response = llm_service.client.chat.completions.create(
                    model=llm_service.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an AI agent in a multi-agent dialogue. Be concise and actionable.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.4,
                )
                content = response.choices[0].message.content.strip()
            except Exception as e:
                content = f"[Dialogue error: {str(e)[:50]}]"
                self.logger.error(f"Dialogue LLM call failed: {e}")

            turn_record = {
                "turn": turn_num,
                "sender": sender,
                "receiver": receiver,
                "performative": performative,
                "content": content,
                "timestamp": time.time(),
                "conversation_id": conversation_id,
            }
            turns.append(turn_record)

            self.logger.info(
                f"[TURN {turn_num}] {sender} → {receiver} ({performative}): "
                f"{content[:80]}..."
            )

            # Check convergence
            if self._check_convergence(turns):
                self.logger.info(
                    f"[DIALOGUE END] Converged in {turn_num} turns "
                    f"(conv={conversation_id})"
                )
                conv["status"] = "converged"
                break

        if conv["status"] != "converged":
            conv["status"] = "max_turns_reached"
            self.logger.info(
                f"[DIALOGUE END] Max turns reached ({self.max_turns}) "
                f"(conv={conversation_id})"
            )

        conv["ended_at"] = time.time()
        return turns

    def _check_convergence(self, turns: List[Dict[str, Any]]) -> bool:
        """Check if the dialogue has reached convergence.

        Convergence is determined by:
        - A CONFIRM performative was used (explicit agreement)
        - Content contains agreement indicators

        Args:
            turns: List of dialogue turn records.

        Returns:
            True if the dialogue has converged.
        """
        if not turns:
            return False

        last_turn = turns[-1]

        # CONFIRM performative = explicit convergence
        if last_turn["performative"] == "CONFIRM":
            return True

        # Check for agreement keywords in content
        agreement_keywords = ["agreed", "confirmed", "finalized", "consensus"]
        content_lower = last_turn["content"].lower()
        if any(kw in content_lower for kw in agreement_keywords):
            return True

        return False

    def get_dialogue_logs(self) -> List[Dict[str, Any]]:
        """Return all dialogue conversation records.

        Returns:
            List of conversation dicts with turns and metadata.
        """
        logs = []
        for conv_id, conv_data in self.conversations.items():
            logs.append({
                "conversation_id": conv_id,
                "agents": f"{conv_data['agent_a']} ↔ {conv_data['agent_b']}",
                "topic": conv_data["topic"][:80],
                "turns": len(conv_data["turns"]),
                "status": conv_data["status"],
                "turn_details": conv_data["turns"],
            })
        return logs
