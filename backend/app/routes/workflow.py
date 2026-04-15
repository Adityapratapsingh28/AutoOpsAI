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
from ..services.orchestrator_service import run_orchestrator, get_or_create_queue, remove_queue
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

    # Pre-create the SSE queue
    get_or_create_queue(workflow_id)

    # Launch orchestrator in background
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
    queue = get_or_create_queue(workflow_id)

    async def event_generator():
        try:
            while True:
                # Wait for next event with a timeout
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=300)
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield {"data": json.dumps({"event": "keepalive", "data": {}})}
                    continue

                yield {"data": msg}
                queue.task_done()

                # Check if stream should end
                try:
                    parsed = json.loads(msg)
                    if parsed.get("event") in ["done", "error"]:
                        break
                except (json.JSONDecodeError, KeyError):
                    pass
        finally:
            remove_queue(workflow_id)

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
