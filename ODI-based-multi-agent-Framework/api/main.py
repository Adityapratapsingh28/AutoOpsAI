"""
FastAPI Server for Multi-Agent Orchestration Framework.

Provides an SSE (Server-Sent Events) endpoint to stream orchestrator 
execution progress to the Next.js frontend in real time.
"""

import asyncio
import json
import traceback
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from orchestrator.meta_orchestrator import MetaOrchestrator
from utils.logger import setup_logger

app = FastAPI(title="Multi-Agent Orchestrator API")

# Allow CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = setup_logger("FastAPI_Server")


@app.get("/api/orchestrate")
async def orchestrate_scenario(
    scenario: str = Query(..., description="The scenario text to execute"),
    model: str = Query("llama-3.3-70b-versatile", description="Groq model to use")
):
    """
    Stream orchestration events using Server-Sent Events (SSE).
    
    Runs the MetaOrchestrator in a background thread and yields 
    progress events to the client in real-time.
    """
    if not scenario.strip():
        raise HTTPException(status_code=400, detail="Scenario cannot be empty")

    logger.info(f"Received request for scenario: {scenario}, model: {model}")

    queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def event_callback(event_type: str, payload: Dict[str, Any]) -> None:
        """Callback to safely push events from the worker thread to the async queue."""
        def push_to_queue():
            # Embed event type INSIDE the data payload (not as a named SSE event)
            # because browser EventSource.onmessage only fires for unnamed events.
            combined = json.dumps({"event": event_type, "data": payload})
            queue.put_nowait(combined)
        loop.call_soon_threadsafe(push_to_queue)

    def run_orchestrator() -> None:
        """Synchronous worker function to run the orchestrator."""
        try:
            from utils.config import Config
            Config.LLM_MODEL = model  # Override model from frontend selection
            orchestrator = MetaOrchestrator()
            orchestrator.execute(scenario, event_callback=event_callback)
        except Exception as e:
            logger.error(f"Orchestration failed: {traceback.format_exc()}")
            event_callback("error", {"message": str(e)})
        finally:
            event_callback("done", {})

    # Start orchestrator in a background thread
    asyncio.create_task(asyncio.to_thread(run_orchestrator))

    async def event_generator():
        """Consumes events from the queue and yields them for the SSE stream."""
        while True:
            msg = await queue.get()
            # Yield as an unnamed SSE event (just data, no event field)
            # so the browser's EventSource.onmessage handler will receive it.
            yield {"data": msg}
            queue.task_done()
            
            # Check if we should stop
            try:
                parsed = json.loads(msg)
                if parsed.get("event") in ["done", "error"]:
                    break
            except Exception:
                pass

    return EventSourceResponse(event_generator())
