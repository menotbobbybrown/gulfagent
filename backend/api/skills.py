"""
Skills marketplace routes — Phase 3 (T48-T52).
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user_id
from core.rate_limiter import limiter
from db.models import Skill, UserSkill, Automation
from db.session import get_db
from db.seed_skills import seed_skills as perform_seed
from agents.scheduler_agent import scheduler

router = APIRouter(prefix="/api/skills", tags=["skills"])

# ──────────────────────────────────────────────
# Pydantic schemas
# ──────────────────────────────────────────────

class SkillResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None
    category: str
    prompt_template: str
    icon: str | None
    default_cron: str | None
    credit_cost: int
    active: bool

    model_config = {"from_attributes": True}


class SingleSkill(BaseModel):
    data: SkillResponse
    error: str | None = None


class ListSkills(BaseModel):
    data: list[SkillResponse]
    error: str | None = None


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@router.post("/seed", status_code=200)
@limiter.limit("10/minute")
async def seed_skills_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Seed the skills table with GCC-specific templates."""
    await perform_seed(db)
    return {"data": {"success": True}}


@router.get("", response_model=ListSkills)
@limiter.limit("30/minute")
async def list_skills(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> ListSkills:
    """List all available skills in the marketplace."""
    result = await db.execute(
        select(Skill)
        .where(Skill.active == True)
        .order_by(Skill.category, Skill.name)
    )
    skills = result.scalars().all()
    return ListSkills(data=[SkillResponse.model_validate(s) for s in skills])


@router.get("/mine", response_model=ListSkills)
@limiter.limit("30/minute")
async def list_my_skills(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> ListSkills:
    """List skills the current user has activated."""
    query = select(Skill).join(UserSkill).where(UserSkill.user_id == user_id)
    result = await db.execute(query)
    skills = result.scalars().all()
    return ListSkills(data=[SkillResponse.model_validate(s) for s in skills])


@router.post("/{slug}/activate", response_model=SingleSkill)
@limiter.limit("10/minute")
async def activate_skill(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> SingleSkill:
    """Activate a skill: creates UserSkill record and an associated Automation."""
    # 1. Get skill
    result = await db.execute(select(Skill).where(Skill.slug == slug))
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail={
            "code": "SKILL_NOT_FOUND",
            "message": f"Skill '{slug}' not found.",
        })

    # 2. Check if already activated
    existing_res = await db.execute(
        select(UserSkill).where(UserSkill.user_id == user_id, UserSkill.skill_id == skill.id)
    )
    if existing_res.scalar_one_or_none():
        return SingleSkill(data=SkillResponse.model_validate(skill))

    # 3. Create UserSkill
    user_skill = UserSkill(user_id=user_id, skill_id=skill.id)
    db.add(user_skill)

    # 4. Auto-create automation if default_cron exists
    if skill.default_cron:
        automation = Automation(
            user_id=user_id,
            name=skill.name,
            prompt=skill.prompt_template,
            cron=skill.default_cron,
            skill_id=skill.id,
            active=True
        )
        db.add(automation)
        await db.commit()
        await db.refresh(automation)

        # Schedule it
        await scheduler.schedule_automation(
            str(automation.id),
            str(user_id),
            automation.prompt,
            automation.cron
        )
    else:
        await db.commit()

    return SingleSkill(data=SkillResponse.model_validate(skill))


@router.delete("/{slug}/deactivate")
@limiter.limit("10/minute")
async def deactivate_skill(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Deactivate a skill: removes UserSkill and any associated automations."""
    # 1. Get skill
    result = await db.execute(select(Skill).where(Skill.slug == slug))
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail={
            "code": "SKILL_NOT_FOUND",
            "message": f"Skill '{slug}' not found.",
        })

    # 2. Remove UserSkill
    await db.execute(
        delete(UserSkill).where(UserSkill.user_id == user_id, UserSkill.skill_id == skill.id)
    )

    # 3. Remove associated automations
    automations_res = await db.execute(
        select(Automation).where(Automation.user_id == user_id, Automation.skill_id == skill.id)
    )
    automations = automations_res.scalars().all()
    for auto in automations:
        await scheduler.remove_automation(str(auto.id))
        await db.delete(auto)

    await db.commit()
    return {"data": {"success": True}}
