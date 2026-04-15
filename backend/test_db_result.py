"""
Fetch the most recent workflow output from DB and display the full email body.
"""
import asyncio, json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.core.database import fetch_one, fetch_all

async def main():
    # Get last workflow
    wf = await fetch_one("""
        SELECT w.id, w.input_text, w.status, w.created_at,
               o.result
        FROM workflows w
        LEFT JOIN outputs o ON o.workflow_id = w.id
        ORDER BY w.created_at DESC
        LIMIT 1
    """)
    
    if not wf:
        print("No workflows found")
        return
    
    print(f"Workflow ID   : {wf['id']}")
    print(f"Status        : {wf['status']}")
    print(f"Input         : {wf['input_text'][:80]}...")
    print()
    
    # Get agents
    agents = await fetch_all("""
        SELECT name, tool, status FROM agents WHERE workflow_id = $1
    """, wf['id'])
    
    print("─" * 60)
    print("AGENTS:")
    for a in agents:
        print(f"  • {a['name']:35} tool={a['tool'] or 'none':20} status={a['status']}")
    
    # Get logs to find tool execution
    logs = await fetch_all("""
        SELECT agent_name, message, level FROM logs WHERE workflow_id = $1
    """, wf['id'])
    
    print()
    print("─" * 60)
    print("TOOL EXECUTION LOGS:")
    for log in logs:
        if any(kw in (log['message'] or '').lower() for kw in 
               ['tool', 'zoom', 'email', 'executed', 'completed', 'sent', 'meet', 'join']):
            print(f"  [{log['agent_name'] or 'system'}] {log['message']}")
    
    # Parse final output
    if wf['result']:
        try:
            result = json.loads(wf['result'])
            print()
            print("─" * 60)
            print("FINAL OUTPUT KEYS:", list(result.keys()))
            
            for item in result.get('results', []):
                agent_name = item.get('agent', '?')
                tool_res = item.get('tool_result', {})
                if tool_res:
                    print(f"\n  Agent '{agent_name}' tool result:")
                    print(json.dumps(tool_res, indent=4))
                    
                # Print email body clearly
                if tool_res.get('has_attachment') is not None or 'body_snippet' in tool_res:
                    print(f"\n  Email Body sent:\n" + "="*60 + "\n" + tool_res.get('body_snippet', '') + "\n" + "="*60)
        except Exception as e:
            print(f"Could not parse result: {e}")

asyncio.run(main())
