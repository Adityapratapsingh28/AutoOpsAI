"""
AutoOps AI — CTDE Governance API.

Provides full CRUD + idempotency for managing agent policies stored in PostgreSQL.

Endpoints:
    GET    /api/governance/policies              - Read all agent policies
    POST   /api/governance/policies              - Add a new master rule (idempotent)
    PATCH  /api/governance/policies              - Edit an existing rule
    DELETE /api/governance/policies              - Delete a specific rule
    GET    /api/governance/insights              - Read recent execution insights
    POST   /api/governance/reload                - Deprecated (Returns success for UI compatibility)
"""

import logging
import json
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..core.security import get_current_user
from ..core.database import fetch_all, fetch_val, execute

logger = logging.getLogger("autoops.governance")

router = APIRouter(prefix="/governance", tags=["CTDE Governance"])


# ── Require manager or admin access ──
def require_manager(user: Dict[str, Any] = Depends(get_current_user)):
    if user.get("role") not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Manager or Admin access required")
    return user


# ─────────────────────────────────────────────
# REQUEST / RESPONSE MODELS
# ─────────────────────────────────────────────

class AddRuleRequest(BaseModel):
    agent_role: str
    category: str   # best_practices | common_failures | optimal_patterns
    rule: str


class UpdateRuleRequest(BaseModel):
    agent_role: str
    category: str
    old_rule: str
    new_rule: str


class DeleteRuleRequest(BaseModel):
    agent_role: str
    category: str
    rule: str


# ─────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────

@router.get("/policies")
async def get_all_policies(user: Dict[str, Any] = Depends(require_manager)):
    """Return structured policies grouped by agent role from PostgreSQL."""
    try:
        rows = await fetch_all("SELECT agent_role, category, rule_text FROM agent_policies")
        
        # Group policies safely
        policies = {}
        for row in rows:
            role = row["agent_role"]
            cat = row["category"]
            rule = row["rule_text"]
            
            if role not in policies:
                policies[role] = {
                    "best_practices": [],
                    "common_failures": [],
                    "optimal_patterns": []
                }
            if cat in policies[role]:
                policies[role][cat].append(rule)

        role_cards = []
        for role, data in policies.items():
            role_cards.append({
                "agent_role": role,
                "best_practices": data["best_practices"],
                "common_failures": data["common_failures"],
                "optimal_patterns": data["optimal_patterns"],
            })
            
        return {
            "total_roles": len(role_cards),
            "policies": role_cards
        }
    except Exception as e:
        logger.error(f"Error fetching policies from DB: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/policies")
async def add_rule(
    body: AddRuleRequest,
    user: Dict[str, Any] = Depends(require_manager)
):
    """Add a new master rule. Idempotent via DB UNIQUE constraint."""
    valid_categories = {"best_practices", "common_failures", "optimal_patterns"}
    if body.category not in valid_categories:
        raise HTTPException(status_code=400, detail="Invalid category")
        
    try:
        # Check if exists
        exists = await fetch_val(
            "SELECT id FROM agent_policies WHERE agent_role = $1 AND category = $2 AND rule_text = $3",
            body.agent_role.strip(), body.category.strip(), body.rule.strip()
        )
        
        if exists:
            return {
                "status": "exists",
                "message": "Rule already exists — no changes made (idempotent).",
                "rule": body.rule
            }
            
        await execute(
            "INSERT INTO agent_policies (agent_role, category, rule_text) VALUES ($1, $2, $3)",
            body.agent_role.strip(), body.category.strip(), body.rule.strip()
        )
        
        return {
            "status": "created",
            "message": f"Rule added to '{body.agent_role}' / '{body.category}'",
            "rule": body.rule
        }
    except Exception as e:
        logger.error(f"Error adding rule to DB: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/policies")
async def update_rule(
    body: UpdateRuleRequest,
    user: Dict[str, Any] = Depends(require_manager)
):
    """Edit an existing rule text."""
    try:
        updated = await execute(
            """
            UPDATE agent_policies 
            SET rule_text = $1 
            WHERE agent_role = $2 AND category = $3 AND rule_text = $4
            """,
            body.new_rule.strip(), body.agent_role.strip(), body.category.strip(), body.old_rule.strip()
        )
        
        if updated == "UPDATE 0":
            raise HTTPException(
                status_code=404,
                detail=f"Rule not found in '{body.agent_role}' / '{body.category}'"
            )
            
        return {
            "status": "updated",
            "message": f"Rule updated in '{body.agent_role}' / '{body.category}'",
            "new_rule": body.new_rule
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating rule in DB: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/policies")
async def delete_rule(
    body: DeleteRuleRequest,
    user: Dict[str, Any] = Depends(require_manager)
):
    """Delete a specific rule."""
    try:
        deleted = await execute(
            "DELETE FROM agent_policies WHERE agent_role = $1 AND category = $2 AND rule_text = $3",
            body.agent_role.strip(), body.category.strip(), body.rule.strip()
        )
        
        if deleted == "DELETE 0":
            raise HTTPException(
                status_code=404,
                detail=f"Rule not found in '{body.agent_role}' / '{body.category}'"
            )
            
        return {
            "status": "deleted",
            "message": f"Rule removed from '{body.agent_role}' / '{body.category}'"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting rule from DB: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights")
async def get_insights(
    limit: int = 20,
    user: Dict[str, Any] = Depends(require_manager)
):
    """Get the N most recent execution insights."""
    try:
        rows = await fetch_all(
            "SELECT insight_data FROM execution_insights ORDER BY created_at DESC LIMIT $1",
            limit
        )
        
        insights = []
        for row in rows:
            raw_data = row["insight_data"]
            if isinstance(raw_data, str):
                insights.append(json.loads(raw_data))
            else:
                insights.append(raw_data)
                
        return {
            "total": len(insights),
            "insights": insights
        }
    except Exception as e:
        logger.error(f"Error fetching insights from DB: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload")
async def reload_policies(user: Dict[str, Any] = Depends(require_manager)):
    """Since data is now in PostgreSQL, this is a no-op that just returns success."""
    return {
        "status": "reloaded",
        "message": "Connected to active PostgreSQL store. No reload required."
    }
