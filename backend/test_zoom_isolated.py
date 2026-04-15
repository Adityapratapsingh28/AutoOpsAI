"""
Isolated test — runs ZoomTool directly (no FastAPI, no orchestrator).
Verifies: credential loading, OAuth token, meeting creation, join_url extraction.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

# Load .env
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.tools.zoom_tool import ZoomTool
from app.core.config import settings

print("=" * 60)
print("ZOOM CREDENTIAL CHECK")
print("=" * 60)
print(f"  ZOOM_ACCOUNT_ID  : '{settings.ZOOM_ACCOUNT_ID}' (len={len(settings.ZOOM_ACCOUNT_ID)})")
print(f"  ZOOM_CLIENT_ID   : '{settings.ZOOM_CLIENT_ID}' (len={len(settings.ZOOM_CLIENT_ID)})")
print(f"  ZOOM_CLIENT_SECRET: '{'*' * len(settings.ZOOM_CLIENT_SECRET)}' (len={len(settings.ZOOM_CLIENT_SECRET)})")
print()

print("=" * 60)
print("RUNNING ZOOM TOOL")
print("=" * 60)

tool = ZoomTool()
result = tool.run(
    input_data={
        "input_text": "schedule a zoom meeting with my engineering team today at 9pm agenda is Agentic AI",
    },
    context={}
)

print("\nZoom Tool Result:")
import json
print(json.dumps(result, indent=2))

print()
if result.get("meeting", {}).get("join_url"):
    print(f"✅ join_url = {result['meeting']['join_url']}")
else:
    print("❌ No join_url in result!")

if result.get("simulated"):
    print("⚠️  Simulated — Zoom API was not called (check credentials or API error above)")
else:
    print("✅ REAL Zoom meeting created!")
