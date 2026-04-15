"""
AutoOps AI — Dashboard Routes.

Provides aggregated statistics for the Employee Portal dashboard.
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any

from ..core.database import fetch_one, fetch_all
from ..core.security import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("")
async def get_dashboard(user: Dict[str, Any] = Depends(get_current_user)):
    """Return dashboard stats for the current user."""

    uid = user["user_id"]

    # Aggregate workflow stats
    total = await fetch_one(
        "SELECT COUNT(*) as count FROM workflows WHERE user_id = $1", uid
    )
    completed = await fetch_one(
        "SELECT COUNT(*) as count FROM workflows WHERE user_id = $1 AND status = 'completed'", uid
    )
    running = await fetch_one(
        "SELECT COUNT(*) as count FROM workflows WHERE user_id = $1 AND status = 'running'", uid
    )
    failed = await fetch_one(
        "SELECT COUNT(*) as count FROM workflows WHERE user_id = $1 AND status = 'failed'", uid
    )
    file_count = await fetch_one(
        "SELECT COUNT(*) as count FROM files WHERE user_id = $1", uid
    )

    total_count = total["count"] if total else 0
    completed_count = completed["count"] if completed else 0

    success_rate = round((completed_count / total_count * 100), 1) if total_count > 0 else 0

    # Recent workflows
    recent = await fetch_all(
        """
        SELECT id, input_text, status, created_at
        FROM workflows
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT 5
        """,
        uid,
    )

    recent_workflows = [
        {
            "id": str(r["id"]),
            "input_text": r["input_text"],
            "status": r["status"],
            "created_at": str(r["created_at"]) if r["created_at"] else None,
        }
        for r in recent
    ]

    return {
        "stats": {
            "total_workflows": total_count,
            "completed": completed_count,
            "running": running["count"] if running else 0,
            "failed": failed["count"] if failed else 0,
            "files": file_count["count"] if file_count else 0,
            "success_rate": success_rate,
        },
        "recent_workflows": recent_workflows,
    }
