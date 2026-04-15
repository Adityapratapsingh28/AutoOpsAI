"""Pydantic schemas for file management endpoints."""

from pydantic import BaseModel
from typing import Optional


class FileResponse(BaseModel):
    id: int
    user_id: int
    file_name: str
    file_path: Optional[str] = None
    created_at: Optional[str] = None


class FileUploadResponse(BaseModel):
    id: int
    file_name: str
    message: str = "File uploaded successfully"
