"""Pydantic schemas for meetings/schedule endpoints."""

from pydantic import BaseModel, Field
from typing import Optional


class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    time: str
    meeting_link: Optional[str] = None


class MeetingResponse(BaseModel):
    id: int
    user_id: int
    title: str
    time: Optional[str] = None
    meeting_link: Optional[str] = None
    created_at: Optional[str] = None
