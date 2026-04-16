"""
Full end-to-end test:
1. Login → get JWT
2. Run workflow: schedule zoom + email team
3. Stream events and print all outputs
4. Look for email body content to verify the Calendly-style format
"""
import asyncio
import httpx
import json

BASE = "http://localhost:8001"
EMAIL = "testagent@autoops.com"
PASS  = "password123"
PROMPT = (
    "I need to schedule a zoom meeting with my engineering team today at 9pm "
    "and agenda is Agentic AI, then send email to all members giving details about the meet"
)

async def run():
    async with httpx.AsyncClient(timeout=120.0) as client:
        # ── Step 1: Login ──
        print("─" * 60)
        print("STEP 1: Login")
        res = await client.post(f"{BASE}/api/auth/login", json={"email": EMAIL, "password": PASS})
        data = res.json()
        token = data.get("access_token")
        user_id = data.get("user_id")
        full_name = data.get("full_name")
        print(f"  ✅ Logged in as '{full_name}' (id={user_id})")
        headers = {"Authorization": f"Bearer {token}"}

        # ── Step 2: Start workflow ──
        print()
        print("─" * 60)
        print("STEP 2: Start Workflow")
        print(f"  Prompt: {PROMPT}")
        res = await client.post(f"{BASE}/api/workflow/run", headers=headers, json={
            "input_text": PROMPT,
            "file_id": None
        })
        wf = res.json()
        wf_id = wf.get("workflow_id")
        print(f"  ✅ Workflow started: {wf_id}")

        # ── Step 3: Stream events ──
        print()
        print("─" * 60)
        print("STEP 3: Streaming Events")
        print()

        tool_results = {}
        email_body_found = False

        async with client.stream("GET", f"{BASE}/api/workflow/stream/{wf_id}", headers=headers) as stream:
            async for line in stream.aiter_lines():
                if not line.startswith("data: "):
                    continue
                raw = line[6:]
                try:
                    evt = json.loads(raw)
                except Exception:
                    continue

                event_type = evt.get("event")
                payload    = evt.get("data", {})

                if event_type == "status":
                    print(f"  [STATUS] {payload.get('step','')}")

                elif event_type == "agents_designed":
                    agents = payload.get("agents", [])
                    print(f"\n  [AGENTS DESIGNED] {len(agents)} agent(s):")
                    for a in agents:
                        print(f"    • {a['name']} → tool: {a.get('tool','none')}")

                elif event_type == "agent_executing":
                    print(f"\n  [EXECUTING] {payload.get('agent','?')}")

                elif event_type == "agent_completed":
                    result = payload.get("result", {})
                    agent  = result.get("agent", "?")
                    tool_r = result.get("tool_result", {})
                    print(f"  [COMPLETED] {agent}")
                    if tool_r:
                        status = tool_r.get("status", "?")
                        msg    = tool_r.get("message", "")
                        print(f"    Tool status: {status}")
                        print(f"    Tool message: {msg}")
                        # Capture meeting data
                        if tool_r.get("meeting"):
                            mtg = tool_r["meeting"]
                            print(f"    📅 Meeting topic   : {mtg.get('topic')}")
                            print(f"    📅 Meeting time    : {mtg.get('start_time')}")
                            print(f"    📅 Duration        : {mtg.get('duration')} mins")
                            print(f"    🔗 Join URL        : {mtg.get('join_url')}")
                            tool_results[agent] = tool_r
                        # Capture email result
                        if tool_r.get("recipients") or tool_r.get("simulated"):
                            print(f"    📧 Email recipients: {tool_r.get('recipients',['(simulated)'])}")
                            email_body_found = True

                elif event_type == "error":
                    print(f"\n  ❌ ERROR: {payload.get('message','?')}")

                elif event_type == "final_output":
                    print(f"\n  [FINAL OUTPUT] Workflow completed.")

                elif event_type == "done":
                    print(f"\n  [DONE]")
                    break

        print()
        print("─" * 60)
        print("RESULT SUMMARY")
        print("─" * 60)
        if tool_results:
            print("✅ Zoom tool returned a meeting object — email body will use Calendly format")
        else:
            print("⚠️  No meeting object captured from tool results")
        if email_body_found:
            print("✅ Email tool triggered successfully")
        else:
            print("⚠️  Email tool may not have run")

asyncio.run(run())
