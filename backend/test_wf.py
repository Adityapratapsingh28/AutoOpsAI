import asyncio
import httpx
import os

async def run_test():
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("1. Logging in...")
        
        login_res = await client.post("http://localhost:8001/api/auth/login", json={
            "email": "testagent@autoops.com",
            "password": "password123"
        })
        
        token = login_res.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
            
        print("2. Starting Workflow (No File)...")
        wf_res = await client.post("http://localhost:8001/api/workflow/run", headers=headers, json={
            "input_text": "I need to schedule a zoom meeting with my engineering team today 9pm and agenda is agentic ai so i will send email to all members giving details about meet",
            "file_id": None
        })
        wf_id = wf_res.json()["workflow_id"]
        print(f"Workflow started: {wf_id}")
        
        print("3. Streaming events...")
        async with client.stream("GET", f"http://localhost:8001/api/workflow/stream/{wf_id}", headers=headers) as stream:
            async for line in stream.aiter_lines():
                if line.startswith("data: "):
                    print(line)
        
if __name__ == "__main__":
    asyncio.run(run_test())
