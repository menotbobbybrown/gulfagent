"""
Automations CRUD — Phase 3 (T40-T44).
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import desc, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user_id
from core.rate_limiter import limiter
from core.usage_tracker import check_automation_limit
from db.models import Automation
from db.session import get_db
from agents.scheduler_agent import scheduler

router = APIRouter(prefix="/api/automations", tags=["automations"])

# ──────────────────────────────────────────────
# Pydantic schemas
# ──────────────────────────────────────────────

class AutomationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    prompt: str = Field(..., min_length=1)
    cron: str = Field(..., min_length=5)
    skill_id: UUID | None = None


class AutomationUpdate(BaseModel):
    name: str | None = None
    prompt: str | None = None
    cron: str | None = None
    active: bool | None = None


class AutomationResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    prompt: str
    cron: str
    active: bool
    skill_id: UUID | None
    last_run: datetime | None
    next_run: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SingleAutomation(BaseModel):
    data: AutomationResponse
    error: str | None = None


class PaginatedAutomations(BaseModel):
    data: list[AutomationResponse]
    meta: dict[str, Any]
    error: str | None = None


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@router.post("", response_model=SingleAutomation, status_code=201)
@limiter.limit("10/minute")
async def create_automation(
    body: AutomationCreate,
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> SingleAutomation:
    # T67 — Check automation limit
    await check_automation_limit(db, user_id)

    automation = Automation(
        user_id=user_id,
        name=body.name,
        prompt=body.prompt,
        cron=body.cron,
        skill_id=body.skill_id,
        active=True
    )
    db.add(automation)
    await db.commit()
    await db.refresh(automation)

    # Register BullMQ repeatable job
    await scheduler.schedule_automation(
        str(automation.id),
        str(user_id),
        automation.prompt,
        automation.cron
    )

    return SingleAutomation(data=AutomationResponse.model_validate(automation))


@router.get("", response_model=PaginatedAutomations)
@limiter.limit("30/minute")
async def list_automations(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> PaginatedAutomations:
    offset = (page - 1) * limit
    query = (
        select(Automation)
        .where(Automation.user_id == user_id)
        .order_by(desc(Automation.created_at))
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    automations = result.scalars().all()

    count_q = select(func.count()).select_from(Automation).where(Automation.user_id == user_id)
    total_result = await db.execute(count_q)
    total = total_result.scalar_one()

    return PaginatedAutomations(
        data=[AutomationResponse.model_validate(a) for a in automations],
        meta={
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        }
    )


@router.get("/{automation_id}", response_model=SingleAutomation)
@limiter.limit("30/minute")
async def get_automation(
    automation_id: UUID,
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> SingleAutomation:
    result = await db.execute(
        select(Automation).where(Automation.id == automation_id, Automation.user_id == user_id)
    )
    automation = result.scalar_one_or_none()
    if not automation:
        raise HTTPException(status_code=404, detail={
            "code": "AUTOMATION_NOT_FOUND",
            "message": "Automation not found.",
        })
    return SingleAutomation(data=AutomationResponse.model_validate(automation))


@router.patch("/{automation_id}", response_model=SingleAutomation)
async def update_automation(
    automation_id: UUID,
    body: AutomationUpdate,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> SingleAutomation:
    result = await db.execute(
        select(Automation).where(Automation.id == automation_id, Automation.user_id == user_id)
    )
    automation = result.scalar_one_or_none()
    if not automation:
        raise HTTPException(status_code=404, detail={
            "code": "AUTOMATION_NOT_FOUND",
            "message": "Automation not found.",
        })

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(automation, key, value)

    await db.commit()
    await db.refresh(automation)

    # Handle BullMQ job update
    if "cron" in update_data or "active" in update_data or "prompt" in update_data:
        if automation.active:
            await scheduler.schedule_automation(
                str(automation.id),
                str(user_id),
                automation.prompt,
                automation.cron
            )
        else:
            await scheduler.remove_automation(str(automation.id))

    return SingleAutomation(data=AutomationResponse.model_validate(automation))


@router.delete("/{automation_id}")
async def delete_automation(
    automation_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Automation).where(Automation.id == automation_id, Automation.user_id == user_id)
    )
    automation = result.scalar_one_or_none()
    if not automation:
        raise HTTPException(status_code=404, detail={
            "code": "AUTOMATION_NOT_FOUND",
            "message": "Automation not found.",
        })

    await db.delete(automation)
    await db.commit()

    # Cancel BullMQ job
    await scheduler.remove_automation(str(automation_id))

    return {"data": {"success": True}}
