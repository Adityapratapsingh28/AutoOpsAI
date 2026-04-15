"""
AutoOps AI — File Management Routes.

Handles CSV/file uploads, listing, and deletion.
"""

import os
import uuid
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import Dict, Any, List

from ..core.database import fetch_all, fetch_one, execute, fetch_val
from ..core.security import get_current_user
from ..core.config import settings
from ..schemas.files import FileResponse, FileUploadResponse

router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Upload a file (CSV, etc.) and register it in the database."""

    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Generate unique filename to avoid collisions
    ext = os.path.splitext(file.filename)[1] if file.filename else ".csv"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_name)

    # Save file to disk
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Register in database
    file_id = await fetch_val(
        """
        INSERT INTO files (user_id, file_name, file_path)
        VALUES ($1, $2, $3)
        RETURNING id
        """,
        user["user_id"], file.filename, file_path,
    )

    return FileUploadResponse(id=file_id, file_name=file.filename)


@router.get("", response_model=List[FileResponse])
async def list_files(user: Dict[str, Any] = Depends(get_current_user)):
    """List all files uploaded by the current user."""

    rows = await fetch_all(
        """
        SELECT id, user_id, file_name, file_path, created_at
        FROM files
        WHERE user_id = $1
        ORDER BY created_at DESC
        """,
        user["user_id"],
    )

    return [
        FileResponse(
            id=r["id"],
            user_id=r["user_id"],
            file_name=r["file_name"],
            file_path=r["file_path"],
            created_at=str(r["created_at"]) if r["created_at"] else None,
        )
        for r in rows
    ]


@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Delete a file by ID."""

    row = await fetch_one(
        "SELECT id, file_path FROM files WHERE id = $1 AND user_id = $2",
        file_id, user["user_id"],
    )
    if not row:
        raise HTTPException(status_code=404, detail="File not found")

    # Remove from disk
    if row["file_path"] and os.path.exists(row["file_path"]):
        os.remove(row["file_path"])

    # Remove from database
    await execute("DELETE FROM files WHERE id = $1", file_id)

    return {"message": "File deleted successfully"}


@router.post("/{file_id}/summarize")
async def summarize_file(
    file_id: int,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Generate an LLM-powered summary of a file."""
    row = await fetch_one(
        "SELECT id, file_path, file_name FROM files WHERE id = $1 AND user_id = $2",
        file_id, user["user_id"],
    )
    if not row:
        raise HTTPException(status_code=404, detail="File not found")

    from ..tools.data_summarizer_tool import DataSummarizerTool
    tool = DataSummarizerTool()
    result = tool.run(
        {"file_path": row["file_path"], "input_text": "summarize this file"},
        {"user_id": user["user_id"]},
    )

    if result.get("status") == "failed":
        raise HTTPException(status_code=500, detail=result.get("error", "Summary failed"))

    return result


@router.post("/{file_id}/ask")
async def ask_about_file_endpoint(
    file_id: int,
    body: Dict[str, Any],
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Ask a question about a file using LLM."""
    question = body.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    row = await fetch_one(
        "SELECT id, file_path, file_name FROM files WHERE id = $1 AND user_id = $2",
        file_id, user["user_id"],
    )
    if not row:
        raise HTTPException(status_code=404, detail="File not found")

    from ..tools.data_summarizer_tool import ask_about_file
    result = ask_about_file(row["file_path"], question)

    if result.get("status") == "failed":
        raise HTTPException(status_code=500, detail=result.get("error", "Q&A failed"))

    return result

