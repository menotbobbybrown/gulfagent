from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Any
from config import get_settings
from api.deps import get_current_admin
from db.session import get_db
from core.model_orchestrator import orchestrator, MODEL_ROUTES
from uuid import UUID

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
