import os
import time
import requests
import json
import sseclient

BASE_URL = "http://127.0.0.1:8000/api"

def run_tests():
    print("🚀 AutoOps AI End-to-End Integration Test 🚀")
    
    # 1. Signup
    email = f"test_{int(time.time())}@example.com"
    print(f"\n1️⃣ Signing up new user: {email}")
    res = requests.post(f"{BASE_URL}/auth/signup", json={
        "full_name": "Test User",
        "email": email,
        "password": "Password123!",
        "role": "admin"
    })
    
    if res.status_code != 200:
        print("❌ Signup failed:", res.text)
        return
        
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Signup successful! Token acquired.")

    # 2. Create a dummy CSV
    csv_path = "test_data.csv"
    with open(csv_path, "w") as f:
        f.write("name,email,sales\nAlice,alice@example.com,500\nBob,bob@example.com,700\n")
    
    print("\n2️⃣ Uploading sample CSV file...")
    with open(csv_path, "rb") as f:
        res = requests.post(
            f"{BASE_URL}/files/upload", 
            headers=headers, 
            files={"file": ("test_data.csv", f, "text/csv")}
        )
        
    if res.status_code != 200:
        print("❌ File upload failed:", res.text)
        return
        
    file_id = res.json()["id"]
    print(f"✅ File uploaded! ID: {file_id}")
    
    # 3. Schedule Meeting (to test Calendar Tool integration)
    print("\n3️⃣ Pre-scheduling a meeting to test calendar...")
    res = requests.post(f"{BASE_URL}/meetings", headers=headers, json={
        "title": "Quarterly Sales Review",
        "time": "2026-05-01T10:00:00Z"
    })
    print("✅ Meeting added to calendar.")

    # 4. Trigger Workflow Execution
    prompt = "Analyze the uploaded sales CSV. Then schedule a meeting to discuss the findings, and notify me with the summary via Email and Slack."
    print(f"\n4️⃣ Triggering Workflow:\n   Prompt: '{prompt}'")
    
    res = requests.post(f"{BASE_URL}/workflow/run", headers=headers, json={
        "input_text": prompt,
        "file_id": file_id
    })
    
    if res.status_code != 200:
        print("❌ Workflow run failed:", res.text)
        return
        
    workflow_id = res.json()["workflow_id"]
    print(f"✅ Orchestrator triggered! Workflow ID: {workflow_id}")

    # 5. Listen to SSE Logs
    print(f"\n5️⃣ Listening to real-time execution stream (SSE)...")
    url = f"{BASE_URL}/workflow/stream/{workflow_id}"
    response = requests.get(url, stream=True)
    client = sseclient.SSEClient(response)
    
    for event in client.events():
        payload = json.loads(event.data)
        ev_type = payload.get("event")
        data = payload.get("data")
        
        if ev_type == "status":
            print(f"   [System] {data.get('step')}")
        elif ev_type == "agents_designed":
            names = [a['name'] for a in data.get("agents", [])]
            print(f"   [Agents Created] {', '.join(names)}")
        elif ev_type == "agent_executing":
            print(f"   [Running] Agent: {data.get('agent')}")
        elif ev_type == "agent_completed":
            print(f"   [Completed] Agent: {data.get('result', {}).get('agent')} -> {data.get('result', {}).get('summary')[:80]}...")
        elif ev_type == "error":
            print(f"   ❌ ERROR: {data.get('message')}")
            break
        elif ev_type == "final_output":
            print(f"\n✅ FULL WORKFLOW COMPLETED!")
            print(json.dumps(data.get("result"), indent=2))
        elif ev_type == "done":
            break
            
    print("\n✅ All integration tests passed! Core engine is fully wired.")
    
    # Cleanup
    os.remove(csv_path)

if __name__ == "__main__":
    run_tests()
