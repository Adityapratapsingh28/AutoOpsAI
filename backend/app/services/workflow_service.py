"""
AutoOps AI — Workflow Service.

Business logic for creating, querying, and managing workflows in the database.
"""

import uuid
import json
from typing import Any, Dict, List, Optional

from ..core.database import fetch_one, fetch_all, execute, fetch_val


async def create_workflow(user_id: int, input_text: str, file_id: Optional[int] = None) -> str:
    """
    Create a new workflow entry in the database.

    Returns the workflow UUID as a string.
    """
    workflow_id = str(uuid.uuid4())

    await execute(
        """
        INSERT INTO workflows (id, user_id, input_text, status)
        VALUES ($1, $2, $3, 'pending')
        """,
        workflow_id, user_id, input_text,
    )

    # Link file to workflow if provided
    if file_id:
        await execute(
            "INSERT INTO workflow_files (workflow_id, file_id) VALUES ($1, $2)",
            workflow_id, file_id,
        )

    return workflow_id


async def get_workflow(workflow_id: str) -> Optional[Dict[str, Any]]:
    """Get a workflow by ID with its agents, logs, and output."""

    # Fetch workflow
    wf = await fetch_one(
        "SELECT id, user_id, input_text, status, created_at FROM workflows WHERE id = $1",
        workflow_id,
    )
    if not wf:
        return None

    # Fetch agents
    agents = await fetch_all(
        """
        SELECT id, workflow_id, name, tool, status, started_at, completed_at
        FROM agents WHERE workflow_id = $1
        ORDER BY id
        """,
        workflow_id,
    )

    # Fetch logs
    logs = await fetch_all(
        """
        SELECT id, workflow_id, agent_name, message, level, created_at
        FROM logs WHERE workflow_id = $1
        ORDER BY created_at
        """,
        workflow_id,
    )

    # Fetch output
    output = await fetch_one(
        "SELECT id, workflow_id, result, created_at FROM outputs WHERE workflow_id = $1",
        workflow_id,
    )

    return {
        "workflow": {
            "id": str(wf["id"]),
            "user_id": wf["user_id"],
            "input_text": wf["input_text"],
            "status": wf["status"],
            "created_at": str(wf["created_at"]) if wf["created_at"] else None,
        },
        "agents": [
            {
                "id": a["id"],
                "workflow_id": str(a["workflow_id"]),
                "name": a["name"],
                "tool": a["tool"],
                "status": a["status"],
                "started_at": str(a["started_at"]) if a["started_at"] else None,
                "completed_at": str(a["completed_at"]) if a["completed_at"] else None,
            }
            for a in agents
        ],
        "logs": [
            {
                "id": l["id"],
                "workflow_id": str(l["workflow_id"]),
                "agent_name": l["agent_name"],
                "message": l["message"],
                "level": l["level"],
                "created_at": str(l["created_at"]) if l["created_at"] else None,
            }
            for l in logs
        ],
        "output": {
            "id": output["id"],
            "workflow_id": str(output["workflow_id"]),
            "result": json.loads(output["result"]) if isinstance(output["result"], str) else output["result"],
            "created_at": str(output["created_at"]) if output["created_at"] else None,
        } if output else None,
    }


async def get_workflow_history(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Get all workflows for a user, ordered by recency."""

    rows = await fetch_all(
        """
        SELECT w.id, w.input_text, w.status, w.created_at,
               COUNT(DISTINCT a.id) as agent_count
        FROM workflows w
        LEFT JOIN agents a ON a.workflow_id = w.id
        WHERE w.user_id = $1
        GROUP BY w.id, w.input_text, w.status, w.created_at
        ORDER BY w.created_at DESC
        LIMIT $2
        """,
        user_id, limit,
    )

    return [
        {
            "id": str(r["id"]),
            "input_text": r["input_text"],
            "status": r["status"],
            "created_at": str(r["created_at"]) if r["created_at"] else None,
            "agent_count": r["agent_count"],
        }
        for r in rows
    ]
