"""
T29 — GET /api/approvals/pending — list pending approvals
T30 — POST /api/approvals/{id}/decide — approve or deny
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user_id
from core.approval_manager import decide_approval, get_pending_approvals
from db.session import get_db

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


# ── Schemas ───────────────────────────────────

class ApprovalResponse(BaseModel):
    id: str
    task_id: str
    action_type: str
    action_payload: dict[str, Any]
    decision: str | None
    expires_at: datetime
    decided_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DecideRequest(BaseModel):
    decision: str = Field(..., pattern="^(approved|denied)$")


# ── Routes ────────────────────────────────────

@router.get("/pending")
async def list_pending_approvals(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """T29 — Return all open (undecided, unexpired) approvals for the current user."""
    approvals = await get_pending_approvals(db, user_id)
    return {
        "data": [ApprovalResponse.model_validate(a) for a in approvals],
        "error": None,
    }


@router.post("/{approval_id}/decide")
async def decide(
    approval_id: str,
    body: DecideRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """T30 — Record approve / deny decision."""
    approval = await decide_approval(db, approval_id, user_id, body.decision)
    return {
        "data": ApprovalResponse.model_validate(approval),
        "error": None,
    }
