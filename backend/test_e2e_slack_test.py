import asyncio
from httpx import AsyncClient

async def run():
    async with AsyncClient(base_url="http://localhost:8001", timeout=120.0) as client:
        # 1. Login
        login_res = await client.post("/api/auth/login", json={"email": "testagent@autoops.com", "password": "password123"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Start workflow
        prompt = "Schedule a Zoom meeting for the engineering team today at 5:00 PM to discuss the new AI integration. Email the team, and broadcast the meeting details on Slack."
        run_res = await client.post("/api/workflow/run", json={"input_text": prompt, "file_id": None}, headers=headers)
        wf_id = run_res.json().get("workflow_id")
        print(f"Workflow ID: {wf_id}")
        
        import time
        # 3. Stream to get agent outcomes
        async with client.stream("GET", f"/api/workflow/stream/{wf_id}", headers=headers) as stream:
            async for line in stream.aiter_lines():
                if not line.startswith("data: "):
                    continue
                raw = line[6:]
                import json
                try:
                    evt = json.loads(raw)
                except Exception:
                    continue

                if evt.get("event") == "agent_completed":
                    print(evt.get("data", {}).get("result", {}).get("agent"))
                    print(evt.get("data", {}).get("result", {}).get("tool_result"))

asyncio.run(run())
