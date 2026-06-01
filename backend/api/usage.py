"""
GET /api/usage — current user usage summary
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user_id
from core.usage_tracker import get_usage_summary
from db.session import get_db

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("")
async def get_usage(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    summary = await get_usage_summary(db, user_id)
    return {"data": summary, "error": None}
