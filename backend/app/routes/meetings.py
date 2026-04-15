"""
AutoOps AI — Meeting / Schedule Routes.

CRUD operations for meetings and calendar integration.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List

from ..core.database import fetch_all, fetch_one, execute, fetch_val
from ..core.security import get_current_user
from ..schemas.meetings import MeetingCreate, MeetingResponse

router = APIRouter(prefix="/meetings", tags=["Meetings"])


@router.get("", response_model=List[MeetingResponse])
async def list_meetings(user: Dict[str, Any] = Depends(get_current_user)):
    """List all meetings for the current user."""

    rows = await fetch_all(
        """
        SELECT id, user_id, title, time, meeting_link, created_at
        FROM meetings
        WHERE user_id = $1
        ORDER BY created_at DESC
        """,
        user["user_id"],
    )

    return [
        MeetingResponse(
            id=r["id"],
            user_id=r["user_id"],
            title=r["title"],
            time=r["time"],
            meeting_link=r["meeting_link"],
            created_at=str(r["created_at"]) if r["created_at"] else None,
        )
        for r in rows
    ]


@router.post("", response_model=MeetingResponse)
async def create_meeting(
    req: MeetingCreate,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Create a new meeting entry."""

    meeting_id = await fetch_val(
        """
        INSERT INTO meetings (user_id, title, time, meeting_link)
        VALUES ($1, $2, $3, $4)
        RETURNING id
        """,
        user["user_id"], req.title, req.time, req.meeting_link,
    )

    return MeetingResponse(
        id=meeting_id,
        user_id=user["user_id"],
        title=req.title,
        time=req.time,
        meeting_link=req.meeting_link,
    )


@router.delete("/{meeting_id}")
async def delete_meeting(
    meeting_id: int,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Delete a meeting by ID."""

    row = await fetch_one(
        "SELECT id FROM meetings WHERE id = $1 AND user_id = $2",
        meeting_id, user["user_id"],
    )
    if not row:
        raise HTTPException(status_code=404, detail="Meeting not found")

    await execute("DELETE FROM meetings WHERE id = $1", meeting_id)
    return {"message": "Meeting deleted successfully"}
