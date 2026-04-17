import os
import uuid
import time
import random
from langfuse import Langfuse, propagate_attributes
from langfuse.types import TraceContext

# Configuration
os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-8df166c5-d6c4-4723-96fc-89c987f9ec7d"
os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-c8fc9c40-c2b8-4550-8db7-c4be6c443a01"
os.environ["LANGFUSE_HOST"] = "https://cloud.langfuse.com"

client = Langfuse()

MODELS = ["gpt-4o", "gpt-3.5-turbo", "claude-3-opus", "gemini-pro"]
USERS = ["1", "2", "3", "4"]
SCENARIOS = [
    "Generate a quarterly sales report for the engineering team.",
    "Analyze the latest customer feedback CSV and summarize trends.",
    "Schedule a zoom meeting for the project kickoff.",
    "Send a slack alert if the database latency exceeds 200ms.",
    "Sync the calendar events from Gmail to Outlook."
]

def populate():
    print("🚀 Populating Langfuse Dashboard with 'Cool' Data...")
    
    for i in range(12):
        workflow_id = str(uuid.uuid4()).replace("-", "")
        user_id = random.choice(USERS)
        model = random.choice(MODELS)
        scenario = random.choice(SCENARIOS)
        
        print(f"Creating trace {i+1}: {scenario[:30]}...")
        
        # 1. Start Trace with propagated attributes
        with propagate_attributes(
            user_id=user_id,
            tags=["demo", "synthetic"]
        ):
            with client.start_as_current_observation(
                name=f"Workflow: {scenario[:40]}...",
                trace_context=TraceContext(trace_id=workflow_id),
                metadata={"input": scenario, "env": "production"}
            ):
                
                # 2. Design Phase (Generation)
                with client.start_as_current_observation(
                    name="Orchestrator: Agent Design",
                    as_type="generation",
                    input=scenario
                ):
                    time.sleep(0.5)
                    # Mock LLM Generation
                    p_toks = random.randint(500, 1500)
                    c_toks = random.randint(200, 600)
                    
                    client.update_current_generation(
                        model=model,
                        usage_details={
                            "prompt_tokens": p_toks,
                            "completion_tokens": c_toks,
                            "total_tokens": p_toks + c_toks
                        },
                        output="{'agents': [{'name': 'DataAnalyst', 'role': 'Analyst'}]}"
                    )
                
                # 3. Execution Phase (Nested Generations)
                for j in range(random.randint(1, 3)):
                    agent_name = f"Agent_{j}"
                    with client.start_as_current_observation(
                        name=f"Agent Execution: {agent_name}",
                        as_type="generation",
                        metadata={"agent": agent_name}
                    ):
                        time.sleep(0.3)
                        pt = random.randint(300, 800)
                        ct = random.randint(100, 400)
                        client.update_current_generation(
                            model=model,
                            usage_details={
                                "prompt_tokens": pt,
                                "completion_tokens": ct,
                                "total_tokens": pt + ct
                            },
                            output=f"Agent {j} logic complete."
                        )
                
                # 4. Score the Trace
                score_val = random.uniform(0.7, 1.0)
                client.score_current_trace(
                    name="System Success",
                    value=score_val,
                    comment="Automated quality check"
                )
                
                if random.random() > 0.7:
                    client.score_current_trace(
                        name="User Feedback",
                        value=1,
                        comment="User liked the result"
                    )

    print("✅ Dashboard population complete! Check your Langfuse UI.")

if __name__ == "__main__":
    populate()
