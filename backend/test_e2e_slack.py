import asyncio
from httpx import AsyncClient

async def run():
    async with AsyncClient(base_url="http://127.0.0.1:8001", timeout=30.0) as client:
        # 1. Login
        login_res = await client.post("/api/auth/login", json={"email": "testagent@autoops.com", "password": "password123"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Start workflow
        prompt = "Schedule a Zoom meeting for the engineering team today at 5:00 PM to discuss the new AI integration. Email the team, and broadcast the meeting details on Slack so they have the join link."
        run_res = await client.post("/api/workflow/run", json={"prompt": prompt}, headers=headers)
        wf_id = run_res.json()["workflow_id"]
        print(f"Workflow ID: {wf_id}")
        
        # 3. Wait for it to finish and read output
        import time
        for _ in range(60):
            res = await client.get(f"/api/workflow/{wf_id}", headers=headers)
            status = res.json().get("status")
            if status in ["completed", "failed"]:
                print("STATUS:", status)
                print("AGENTS:", res.json().get("agents"))
                break
            time.sleep(2)

asyncio.run(run())
