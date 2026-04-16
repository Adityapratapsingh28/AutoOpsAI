"""
AutoOps AI — Workflow Routes (CORE FEATURE).

Handles workflow execution, SSE streaming, history, and detail views.
This is the most important route module in the application.
"""

import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict, Any
from sse_starlette.sse import EventSourceResponse

from ..core.security import get_current_user
from ..services.workflow_service import create_workflow, get_workflow, get_workflow_history
from ..services.orchestrator_service import run_orchestrator
from ..core.cache import get_redis
from ..schemas.workflow import WorkflowRunRequest

router = APIRouter(prefix="/workflow", tags=["Workflows"])


@router.post("/run")
async def run_workflow(
    req: WorkflowRunRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Submit a workflow for execution.

    Creates a workflow record in the DB, then launches the MetaOrchestrator
    in a background task. Returns the workflow_id immediately so the client
    can open an SSE connection for real-time streaming.
    """
    # Create workflow in DB
    workflow_id = await create_workflow(
        user_id=user["user_id"],
        input_text=req.input_text,
        file_id=req.file_id,
    )

    # Push to Redis Queue for background worker
    client = await get_redis()
    if client:
        payload = json.dumps({
            "workflow_id": workflow_id,
            "input_text": req.input_text,
            "user_id": user["user_id"],
            "file_id": req.file_id
        })
        await client.lpush("orchestrator_queue", payload)
    else:
        # Fallback to direct background task if Redis is unavailable
        loop = asyncio.get_running_loop()
        asyncio.create_task(
            run_orchestrator(workflow_id, req.input_text, user["user_id"], loop, req.file_id)
        )

    return {
        "workflow_id": workflow_id,
        "status": "started",
        "message": "Workflow execution started. Connect to SSE stream for real-time updates.",
        "stream_url": f"/workflow/stream/{workflow_id}",
    }


@router.get("/stream/{workflow_id}")
async def stream_workflow(workflow_id: str):
    """
    SSE endpoint for real-time workflow execution streaming.

    Events streamed:
      - status: Pipeline progress steps
      - agents_designed: Agent configurations
      - agent_executing: Agent started
      - agent_completed: Agent finished
      - final_output: Complete workflow result
      - error: Execution error
      - done: Stream complete
    """
    async def event_generator():
        client = await get_redis()
        if not client:
            yield {"data": json.dumps({"event": "error", "data": {"message": "Redis unavailable. Cannot stream results."}})}
            return
            
        pubsub = client.pubsub()
        await pubsub.subscribe(f"workflow:{workflow_id}:stream")
        
        try:
            while True:
                try:
                    # Pubsub.get_message with timeout to allow keepalives
                    msg = await asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True), timeout=300)
                except asyncio.TimeoutError:
                    yield {"data": json.dumps({"event": "keepalive", "data": {}})}
                    continue

                if msg and msg["type"] == "message":
                    data = msg["data"]
                    yield {"data": data}
                    
                    try:
                        parsed = json.loads(data)
                        if parsed.get("event") in ["done", "error"]:
                            break
                    except (json.JSONDecodeError, KeyError):
                        pass
                else:
                    await asyncio.sleep(0.1) # Prevent busy waiting if no msg immediately
        finally:
            await pubsub.unsubscribe(f"workflow:{workflow_id}:stream")
            await pubsub.close()

    return EventSourceResponse(event_generator())


@router.get("/history")
async def workflow_history(
    user: Dict[str, Any] = Depends(get_current_user),
    limit: int = 50,
):
    """Get the current user's workflow history."""
    history = await get_workflow_history(user["user_id"], limit)
    return {"workflows": history}


@router.get("/{workflow_id}")
async def get_workflow_detail(
    workflow_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Get full details of a workflow including agents, logs, and output."""
    detail = await get_workflow(workflow_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Verify ownership
    if detail["workflow"]["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to view this workflow")

    return detail
