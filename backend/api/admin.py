from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Any
from config import get_settings
from api.deps import get_current_admin
from db.session import get_db
from core.model_orchestrator import orchestrator, MODEL_ROUTES
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/admin", tags=["admin"])
settings = get_settings()

class OrchestratorTestRequest(BaseModel):
    prompt: str
    task_type: str = "simple_qa"

@router.get("/orchestrator/status")
async def get_orchestrator_status(user_id: UUID = Depends(get_current_admin)):
    stats = orchestrator.get_stats()
    return {
        "data": {
            "available_routes": list(MODEL_ROUTES.keys()),
            "cost_today_usd": await orchestrator.get_cost_today(),
            "cost_month_usd": await orchestrator.get_cost_this_month(),
            **stats
        },
        "error": None
    }

@router.post("/orchestrator/test")
async def test_orchestrator(
    body: OrchestratorTestRequest,
    user_id: UUID = Depends(get_current_admin)
):
    try:
        result = await orchestrator.run(
            task_type=body.task_type,
            prompt=body.prompt,
            user_tier="pro" # Test with pro tier to see primary models
        )
        return {"data": result, "error": None}
    except Exception as e:
        return {"data": None, "error": {"message": str(e)}}

@router.post("/users/{user_id}/make-admin")
async def make_admin(user_id: UUID, admin_id: UUID = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    from db.models import User
    from sqlalchemy import select, update
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")
    await db.execute(update(User).where(User.id == user_id).values(is_admin=True))
    await db.commit()
    return {"data": {"success": True, "user_id": str(user_id)}, "error": None}

@router.get("/users")
async def list_users(admin_id: UUID = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    from db.models import User
    from sqlalchemy import select, func
    result = await db.execute(select(User).order_by(User.created_at.desc()).limit(100))
    users = result.scalars().all()
    user_list = []
    for u in users:
        count_res = await db.execute(select(func.count()).where(User.id == u.id))  # placeholder
        user_list.append({"id": str(u.id), "email": u.email, "tier": u.subscription_tier, "is_admin": u.is_admin, "created_at": u.created_at.isoformat() if u.created_at else None})
    return {"data": user_list, "error": None}
