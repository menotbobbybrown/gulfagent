"""
T09 — Usage tracker.
- check_credits_before_task: raise 403 if user is over limit
- deduct_credits_after_task: called after task completes successfully
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from fastapi import HTTPException

from db.models import Usage, User
from config import get_settings

settings = get_settings()

TIER_LIMITS: dict[str, int] = {
    "basic": settings.credits_basic,
    "pro": settings.credits_pro,
    "enterprise": 999_999_999,
}

TIER_TASK_LIMITS: dict[str, int] = {
    "basic": settings.task_limit_basic,
    "pro": settings.task_limit_pro,
    "enterprise": 999_999_999,
}


def _year_month() -> str:
    return datetime.utcnow().strftime("%Y-%m")


async def _get_or_create_usage(session: AsyncSession, user_id: UUID, credits_limit: int) -> Usage:
    ym = _year_month()
    result = await session.execute(
        select(Usage).where(Usage.user_id == user_id, Usage.year_month == ym)
    )
    record = result.scalar_one_or_none()
    if record:
        return record

    # upsert to avoid race
    stmt = (
        pg_insert(Usage)
        .values(user_id=user_id, year_month=ym, credits_limit=credits_limit)
        .on_conflict_do_nothing()
        .returning(Usage)
    )
    result = await session.execute(stmt)
    await session.commit()
    # re-fetch after potential conflict
    result = await session.execute(
        select(Usage).where(Usage.user_id == user_id, Usage.year_month == ym)
    )
    return result.scalar_one()


async def check_credits_before_task(
    session: AsyncSession,
    user_id: UUID,
    estimated_cost: int = 1,
) -> None:
    """Raise 403 if user has exceeded their monthly credit limit."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    limit = TIER_LIMITS.get(user.subscription_tier, settings.credits_basic)
    usage = await _get_or_create_usage(session, user_id, limit)

    if usage.credits_used + estimated_cost > limit:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "CREDITS_EXCEEDED",
                "message": "Monthly credit limit reached. Please upgrade your plan.",
                "credits_used": usage.credits_used,
                "credits_limit": limit,
                "tier": user.subscription_tier,
            },
        )


async def deduct_credits_after_task(
    session: AsyncSession,
    user_id: UUID,
    credits: int,
    tasks_delta: int = 1,
) -> Usage:
    """Increment usage record after task completes. Credits must be > 0."""
    if credits <= 0:
        credits = 1

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    limit = TIER_LIMITS.get(user.subscription_tier if user else "basic", settings.credits_basic)

    usage = await _get_or_create_usage(session, user_id, limit)

    await session.execute(
        update(Usage)
        .where(Usage.user_id == user_id, Usage.year_month == _year_month())
        .values(
            credits_used=Usage.credits_used + credits,
            tasks_run=Usage.tasks_run + tasks_delta,
            updated_at=datetime.utcnow(),
        )
    )
    await session.commit()
    await session.refresh(usage)
    return usage


async def get_usage_summary(session: AsyncSession, user_id: UUID) -> dict:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    limit = TIER_LIMITS.get(user.subscription_tier, settings.credits_basic)
    usage = await _get_or_create_usage(session, user_id, limit)

    return {
        "year_month": usage.year_month,
        "credits_used": usage.credits_used,
        "credits_limit": limit,
        "credits_remaining": max(0, limit - usage.credits_used),
        "tasks_run": usage.tasks_run,
        "task_limit": TIER_TASK_LIMITS.get(user.subscription_tier, settings.task_limit_basic),
        "tier": user.subscription_tier,
        "percentage_used": round((usage.credits_used / limit) * 100, 1) if limit else 0,
    }
