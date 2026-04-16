"""
AutoOps AI — Orchestrator Service (Bridge to Core Engine).

This is the CRITICAL integration layer that wraps the existing
MetaOrchestrator without modifying it. It:
  1. Adds the core engine directory to sys.path
  2. Imports and runs MetaOrchestrator.execute()
  3. Captures events via event_callback
  4. Pushes events to SSE queues for real-time streaming
  5. Persists agents, logs, and outputs to PostgreSQL
"""

import sys
import os
import asyncio
import json
import logging
import traceback
from typing import Any, Dict, Optional, Callable
from datetime import datetime

from ..core.config import settings
from ..core.database import execute, fetch_val
from ..core.cache import cache_delete, key_dashboard, key_governance_insights

logger = logging.getLogger("autoops.orchestrator_service")

# ── Per-workflow SSE queues ──
_workflow_queues: Dict[str, asyncio.Queue] = {}


def get_or_create_queue(workflow_id: str) -> asyncio.Queue:
    """Get or create an SSE event queue for a workflow."""
    if workflow_id not in _workflow_queues:
        _workflow_queues[workflow_id] = asyncio.Queue()
    return _workflow_queues[workflow_id]


def remove_queue(workflow_id: str):
    """Clean up a workflow's SSE queue."""
    _workflow_queues.pop(workflow_id, None)


def _ensure_core_engine_on_path():
    """Add the core engine directory to sys.path if not already present."""
    engine_path = os.path.abspath(settings.CORE_ENGINE_PATH)
    if engine_path not in sys.path:
        sys.path.insert(0, engine_path)
        logger.info(f"Added core engine to sys.path: {engine_path}")


async def run_orchestrator(
    workflow_id: str,
    input_text: str,
    user_id: int,
    loop: asyncio.AbstractEventLoop,
    file_id: Optional[str] = None,
):
    """
    Run the MetaOrchestrator in a background thread.

    This function:
      - Imports and initializes MetaOrchestrator from the existing core engine
      - Calls orchestrator.execute(input_text, event_callback=...)
      - The event_callback pushes events to the SSE queue AND saves to DB
      - Updates workflow status in DB on completion or failure
    """
    queue = get_or_create_queue(workflow_id)

    # Shared store to pass tool results from earlier agents to later ones
    tool_results_store: Dict[str, Any] = {}

    # Store LLM-assigned tool per agent (populated from agents_designed event)
    agent_tool_map: Dict[str, Optional[str]] = {}

    # ── Fetch sender's full_name once — injected into every tool context ──
    sender_full_name = "Your Manager"
    try:
        name_row = await fetch_val(
            "SELECT full_name FROM users WHERE id = $1", user_id
        )
        if name_row:
            sender_full_name = name_row
            logger.info(f"Sender resolved: '{sender_full_name}' (user_id={user_id})")
    except Exception as e:
        logger.warning(f"Could not fetch sender name for user_id={user_id}: {e}")

    # Update workflow status to running
    await execute(
        "UPDATE workflows SET status = 'running' WHERE id = $1",
        workflow_id,
    )
    
    # Invalidate dashboard cache for running state
    await cache_delete(key_dashboard(user_id))

    def _push_event(event_type: str, payload: Dict[str, Any]):
        """Thread-safe push to the async SSE queue."""
        data = json.dumps({"event": event_type, "data": payload})
        loop.call_soon_threadsafe(queue.put_nowait, data)

    def event_callback(event_type: str, payload: Dict[str, Any]):
        """
        Callback passed to MetaOrchestrator.execute().
        Fires from the orchestrator's worker thread.
        """
        try:
            # Push to SSE queue for real-time streaming
            _push_event(event_type, payload)

            # Persist important events to database (fire-and-forget in the loop)
            if event_type == "agent_executing":
                agent_name = payload.get("agent", "unknown")
                asyncio.run_coroutine_threadsafe(
                    _save_agent(workflow_id, agent_name, "running"),
                    loop,
                )
                asyncio.run_coroutine_threadsafe(
                    _save_log(workflow_id, agent_name, f"Agent '{agent_name}' execution started", "info"),
                    loop,
                )
                _push_event("status", {"step": f"🤖 Spawning isolated execution context for Agent [{agent_name}] — injecting role-specific CTDE policies and tool bindings..."})

            elif event_type == "agent_completed":
                result = payload.get("result", {})
                agent_name = result.get("agent", "unknown")
                status = result.get("status", "completed")
                summary = result.get("summary", "")
                
                # --- AUTOOPS EXTERNAL TOOL DISPATCHER INJECTION ---
                tool_output = None

                # Read tool directly from LLM assignment (no keyword guessing)
                tool_name = agent_tool_map.get(agent_name)
                if not tool_name:
                    logger.info(f"Agent '{agent_name}' has no tool assigned (LLM reasoning only).")
                    _push_event("status", {"step": f"📋 Agent [{agent_name}] operating in LLM-reasoning-only mode — no external tool binding required for this task."})
                
                if tool_name and status != "failed":
                    try:
                        from ..services.tool_dispatcher import execute_tool
                        _push_event("status", {"step": f"🔧 Dispatching tool binding [{tool_name}] for Agent [{agent_name}] — routing request through AutoOps Tool Vault..."})
                        
                        # Gather context for the tool (e.g. file pointers, event loop, sender name)
                        context = {
                            "workflow_id": workflow_id,
                            "user_id": user_id,
                            "event_loop": loop,
                            "sender_name": sender_full_name,  # pre-fetched from DB at workflow start
                        }
                        
                        input_data = {
                            "llm_summary": summary,
                            "input_text": input_text,
                        }
                        
                        # Inject results from previous tools so downstream tools can use them
                        if tool_results_store:
                            input_data["previous_tool_results"] = dict(tool_results_store)
                        
                        if file_id:
                            context["file_id"] = file_id
                            # Look up file path
                            file_path = asyncio.run_coroutine_threadsafe(
                                fetch_val("SELECT file_path FROM files WHERE id = $1", int(file_id)),
                                loop
                            ).result()
                            if file_path:
                                input_data["file_path"] = file_path
                            
                        # Execute the backend API tool synchronously
                        tool_output = execute_tool(
                            tool_name=tool_name, 
                            input_data=input_data, 
                            context=context
                        )
                        
                        # Inject backend output back into the agent's LLM result
                        if tool_output:
                            result["tool_result"] = tool_output
                            # Store tool output so downstream tools can use it
                            tool_results_store[agent_name] = tool_output
                            _push_event("status", {"step": f"✅ Tool [{tool_name}] finished execution — output serialized and stored in shared inter-agent context store for downstream agents."})
                    except Exception as e:
                        logger.error(f"Tool execution failed: {e}")
                        result["tool_error"] = str(e)
                # ----------------------------------------------------

                asyncio.run_coroutine_threadsafe(
                    _update_agent(workflow_id, agent_name, status),
                    loop,
                )
                asyncio.run_coroutine_threadsafe(
                    _save_log(workflow_id, agent_name, f"Completed: {summary[:200]}", "info"),
                    loop,
                )
                _push_event("status", {"step": f"✔️  Agent [{agent_name}] report submitted to MetaOrchestrator — result committed to shared execution graph."})

            elif event_type == "status":
                step = payload.get("step", "")
                asyncio.run_coroutine_threadsafe(
                    _save_log(workflow_id, None, step, "info"),
                    loop,
                )

            elif event_type == "agents_designed":
                agents = payload.get("agents", [])
                agent_names = [a.get('name', '?') for a in agents]
                tool_list = [a.get('tool', 'LLM-only') for a in agents]
                _push_event("status", {"step": f"📐 DAG resolved — {len(agents)} agents instantiated: {', '.join(agent_names)}"}) 
                _push_event("status", {"step": f"⚙️  Tool bindings assigned from CTDE Vault: {', '.join([t for t in tool_list if t])}"}) 
                for agent_cfg in agents:
                    name = agent_cfg.get("name", "unknown")
                    # Read tool directly from LLM response — no keyword fallback
                    tool = agent_cfg.get("tool")
                    agent_tool_map[name] = tool
                    logger.info(f"Agent '{name}' → tool: {tool or 'none (LLM only)'}")
                    asyncio.run_coroutine_threadsafe(
                        _save_agent(workflow_id, name, "pending", tool),
                        loop,
                    )

            elif event_type == "error":
                msg = payload.get("message", "Unknown error")
                asyncio.run_coroutine_threadsafe(
                    _save_log(workflow_id, None, f"ERROR: {msg}", "error"),
                    loop,
                )

        except Exception as e:
            logger.error(f"Event callback error: {e}")

    # Run orchestrator in background thread
    def _run():
        try:
            _ensure_core_engine_on_path()

            # Import from core engine (only after path is set)
            from orchestrator.meta_orchestrator import MetaOrchestrator

            logger.info(f"Starting orchestration for workflow {workflow_id}")
            _push_event("status", {"step": "🧠 MetaOrchestrator initializing — loading system configuration and CTDE governance policies from PostgreSQL..."})

            orchestrator = MetaOrchestrator()
            result = orchestrator.execute(input_text, event_callback=event_callback)

            # Save final output to DB
            asyncio.run_coroutine_threadsafe(
                _save_output(workflow_id, result),
                loop,
            )

            # Update workflow status
            asyncio.run_coroutine_threadsafe(
                _update_workflow_status(workflow_id, "completed", user_id),
                loop,
            )

            # Push final output event
            _push_event("final_output", {
                "workflow_id": workflow_id,
                "result": _sanitize_result(result),
            })
            _push_event("done", {})

        except Exception as e:
            logger.error(f"Orchestration failed: {traceback.format_exc()}")
            _push_event("error", {"message": str(e)})
            _push_event("done", {})
            asyncio.run_coroutine_threadsafe(
                _update_workflow_status(workflow_id, "failed", user_id),
                loop,
            )

    # Spawn the blocking orchestrator work in a thread
    await asyncio.to_thread(_run)




# ── Database Helpers ──

async def _save_agent(workflow_id: str, name: str, status: str, tool: Optional[str] = None):
    """Insert or update an agent record."""
    try:
        existing = await fetch_val(
            "SELECT id FROM agents WHERE workflow_id = $1 AND name = $2",
            workflow_id, name,
        )
        if existing:
            if status == "running":
                await execute(
                    "UPDATE agents SET status = $1, started_at = NOW() WHERE workflow_id = $2 AND name = $3",
                    status, workflow_id, name,
                )
            else:
                await execute(
                    "UPDATE agents SET status = $1 WHERE workflow_id = $2 AND name = $3",
                    status, workflow_id, name,
                )
        else:
            await execute(
                "INSERT INTO agents (workflow_id, name, tool, status) VALUES ($1, $2, $3, $4)",
                workflow_id, name, tool, status,
            )
    except Exception as e:
        logger.error(f"Failed to save agent: {e}")


async def _update_agent(workflow_id: str, name: str, status: str):
    """Update agent status and completion time."""
    try:
        await execute(
            "UPDATE agents SET status = $1, completed_at = NOW() WHERE workflow_id = $2 AND name = $3",
            status, workflow_id, name,
        )
    except Exception as e:
        logger.error(f"Failed to update agent: {e}")


async def _save_log(workflow_id: str, agent_name: Optional[str], message: str, level: str):
    """Insert a log entry."""
    try:
        await execute(
            "INSERT INTO logs (workflow_id, agent_name, message, level) VALUES ($1, $2, $3, $4)",
            workflow_id, agent_name, message, level,
        )
    except Exception as e:
        logger.error(f"Failed to save log: {e}")


async def _save_output(workflow_id: str, result: Dict[str, Any]):
    """Insert the final workflow output."""
    try:
        sanitized = _sanitize_result(result)
        await execute(
            "INSERT INTO outputs (workflow_id, result) VALUES ($1, $2)",
            workflow_id, json.dumps(sanitized),
        )
    except Exception as e:
        logger.error(f"Failed to save output: {e}")


async def _update_workflow_status(workflow_id: str, status: str, user_id: Optional[int] = None):
    """Update the workflow status and invalidate cache."""
    try:
        await execute(
            "UPDATE workflows SET status = $1 WHERE id = $2",
            status, workflow_id,
        )
        # Flush insights cache since workflow completed and likely dropped new insights
        if status in ["completed", "failed"]:
            await cache_delete(key_governance_insights())
        if user_id:
            await cache_delete(key_dashboard(user_id))
    except Exception as e:
        logger.error(f"Failed to update workflow status: {e}")


def _sanitize_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Make the orchestrator result JSON-serializable."""
    sanitized = {}
    for key, value in result.items():
        try:
            json.dumps(value)
            sanitized[key] = value
        except (TypeError, ValueError):
            sanitized[key] = str(value)
    return sanitized
