"""
T39 — Link phone number to Supabase user account.
PATCH /api/users/me/phone — update authenticated user's phone number.
GET  /api/users/me       — return user profile.
"""

import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user_id
from db.models import User
from db.session import get_db

router = APIRouter(prefix="/api/users", tags=["users"])

# E.164 regex: +971501234567 — digits only after optional +
_E164_RE = re.compile(r"^\+?[1-9]\d{6,14}$")


class PhoneUpdate(BaseModel):
    phone: str = Field(..., min_length=7, max_length=16)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        normalized = v.strip()
        if not normalized.startswith("+"):
            normalized = f"+{normalized}"
        if not _E164_RE.match(normalized):
            raise ValueError("Phone must be in E.164 format, e.g. +971501234567")
        return normalized


class UserProfile(BaseModel):
    id: str
    email: str
    phone: str | None
    full_name: str | None
    subscription_tier: str
    subscription_status: str
    preferred_language: str

    model_config = {"from_attributes": True}


@router.get("/me")
async def get_profile(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"data": UserProfile.model_validate(user), "error": None}


@router.patch("/me/phone")
async def update_phone(
    body: PhoneUpdate,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    T39 — Save E.164 phone number to user record.
    This enables WhatsApp task submission from that number.
    """
    # Check phone not already claimed by another user
    result = await db.execute(
        select(User).where(User.phone == body.phone, User.id != user_id)
    )
    conflict = result.scalar_one_or_none()
    if conflict:
        raise HTTPException(
            status_code=409,
            detail="This phone number is already linked to another account.",
        )

    await db.execute(
        update(User).where(User.id == user_id).values(phone=body.phone)
    )
    await db.commit()

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    return {"data": UserProfile.model_validate(user), "error": None}


@router.patch("/me/language")
async def update_language(
    language: str,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Set preferred language: en | ar."""
    if language not in ("en", "ar"):
        raise HTTPException(status_code=400, detail="Language must be 'en' or 'ar'")
    await db.execute(
        update(User).where(User.id == user_id).values(preferred_language=language)
    )
    await db.commit()
    return {"data": {"preferred_language": language}, "error": None}
