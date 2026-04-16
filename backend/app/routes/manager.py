"""
AutoOps AI — Manager Portal Routes.

Handles Org Analytics, Teams, Members, Logs, and Reports for managers.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List

from ..core.security import get_current_user
from ..core.database import fetch_all, fetch_one, execute, fetch_val

router = APIRouter(prefix="/manager", tags=["Manager Portal"])

def require_manager(user: Dict[str, Any] = Depends(get_current_user)):
    if user.get("role") not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Manager access required")
    return user

@router.get("/dashboard")
async def get_manager_dashboard(user: Dict[str, Any] = Depends(require_manager)):
    """Org Analytics & High-level Team Stats"""
    # Quick overview metrics
    total_workflows = await fetch_val("SELECT COUNT(*) FROM workflows")
    completed = await fetch_val("SELECT COUNT(*) FROM workflows WHERE status = 'completed'")
    failed = await fetch_val("SELECT COUNT(*) FROM workflows WHERE status = 'failed'")
    
    # E.g., success rate
    success_rate = round((completed / total_workflows) * 100) if total_workflows > 0 else 0
    
    # Activity stream
    recent_activity = await fetch_all("""
        SELECT w.id, w.input_text, w.status, w.created_at, u.full_name as user_name
        FROM workflows w
        JOIN users u ON w.user_id = u.id
        ORDER BY w.created_at DESC
        LIMIT 10
    """)
    
    # Execution time / hours saved (mock assumption: 1 workflow saves 1.5 hours)
    hours_saved = total_workflows * 1.5

    return {
        "stats": {
            "total_workflows": total_workflows,
            "success_rate": success_rate,
            "failed": failed,
            "hours_saved": hours_saved
        },
        "activity": [dict(r) for r in recent_activity]
    }

@router.get("/teams")
async def get_teams(user: Dict[str, Any] = Depends(require_manager)):
    """List all teams"""
    teams = await fetch_all("SELECT * FROM teams ORDER BY name ASC")
    return [dict(t) for t in teams]

@router.post("/teams")
async def create_team(request_data: dict, user: Dict[str, Any] = Depends(require_manager)):
    """Create a new team"""
    name = request_data.get("name")
    description = request_data.get("description", "")
    slug = name.lower().replace(" ", "-") if name else ""
    
    team_id = await fetch_val(
        """
        INSERT INTO teams (name, slug, description, created_by)
        VALUES ($1, $2, $3, $4)
        RETURNING id
        """,
        name, slug, description, user["user_id"]
    )
    return {"id": team_id, "name": name, "status": "created"}

@router.get("/members")
async def get_team_members(user: Dict[str, Any] = Depends(require_manager)):
    """List all team members across the org"""
    members = await fetch_all("""
        SELECT tm.id, tm.team_id, tm.team_name, tm.work_email, tm.designation, tm.role, tm.is_active, u.full_name
        FROM team_members tm
        JOIN users u ON tm.user_id = u.id
        ORDER BY u.full_name ASC
    """)
    return [dict(m) for m in members]

@router.get("/users_list")
async def get_users_list(user: Dict[str, Any] = Depends(require_manager)):
    """List all standard users in the org to assign them to teams"""
    # Assuming all users could be assigned
    users = await fetch_all("SELECT id, full_name, email FROM users ORDER BY full_name ASC")
    return [dict(u) for u in users]

@router.post("/members")
async def assign_team_member(request_data: dict, user: Dict[str, Any] = Depends(require_manager)):
    """Assign a user to a team"""
    user_id = request_data.get("user_id")
    team_id = request_data.get("team_id")
    designation = request_data.get("designation", "Member")
    
    if not user_id or not team_id:
        raise HTTPException(status_code=400, detail="user_id and team_id required")

    # Fetch user details
    target_user = await fetch_one("SELECT full_name, email FROM users WHERE id=$1", user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Fetch team details
    target_team = await fetch_one("SELECT name FROM teams WHERE id=$1", team_id)
    if not target_team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Upsert logic (if user is already in a team, maybe transfer them? For now, just insert or ignore if in this team)
    existing = await fetch_val("SELECT id FROM team_members WHERE user_id=$1 AND team_id=$2", user_id, team_id)
    if existing:
        raise HTTPException(status_code=400, detail="User is already in this team")

    await execute("""
        INSERT INTO team_members (user_id, team_id, team_name, work_email, designation) 
        VALUES ($1, $2, $3, $4, $5)
    """, user_id, team_id, target_team["name"], target_user["email"], designation)
    
    return {"status": "success", "message": "Member assigned successfully"}

@router.get("/reports")
async def get_reports(user: Dict[str, Any] = Depends(require_manager)):
    """Get centralized reports"""
    reports = await fetch_all("""
        SELECT r.id, r.title, r.summary, r.created_at, w.user_id, u.full_name as author
        FROM reports r
        JOIN workflows w ON r.workflow_id = w.id
        JOIN users u ON w.user_id = u.id
        ORDER BY r.created_at DESC
        LIMIT 50
    """)
    # If the reports table doesn't have data, we might need a fallback or wait for data.
    return [dict(r) for r in reports]

@router.get("/logs")
async def get_system_logs(user: Dict[str, Any] = Depends(require_manager)):
    """Get recent system and agent logs for auditing"""
    # Fetch top system logs combining agent logs too for a comprehensive audit
    logs = await fetch_all("""
        SELECT id, workflow_id, agent_name as source, message, level, created_at
        FROM logs
        ORDER BY created_at DESC
        LIMIT 50
    """)
    return [dict(l) for l in logs]
