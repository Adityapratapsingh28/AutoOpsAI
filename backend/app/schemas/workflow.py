"""Pydantic schemas for workflow endpoints."""

from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime


class WorkflowRunRequest(BaseModel):
    input_text: str = Field(..., min_length=1, max_length=2000)
    file_id: Optional[int] = None


class WorkflowResponse(BaseModel):
    id: str
    user_id: int
    input_text: str
    status: str
    created_at: Optional[str] = None


class AgentResponse(BaseModel):
    id: int
    workflow_id: str
    name: str
    tool: Optional[str] = None
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class LogResponse(BaseModel):
    id: int
    workflow_id: str
    agent_name: Optional[str] = None
    message: str
    level: str
    created_at: Optional[str] = None


class OutputResponse(BaseModel):
    id: int
    workflow_id: str
    result: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None


class WorkflowDetailResponse(BaseModel):
    workflow: WorkflowResponse
    agents: List[AgentResponse] = []
    logs: List[LogResponse] = []
    output: Optional[OutputResponse] = None
