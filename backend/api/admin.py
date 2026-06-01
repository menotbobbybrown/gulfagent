from fastapi import APIRouter, HTTPException, Depends
import httpx
from config import get_settings
from api.deps import get_current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])
settings = get_settings()

@router.get("/ollama/status")
async def get_ollama_status(user: dict = Depends(get_current_user)):
    # In a real app, check if user is admin
    base_url = settings.ollama_base_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base_url}/api/tags")
            if resp.status_code == 200:
                return {"data": resp.json(), "error": None}
            else:
                return {"data": None, "error": {"message": f"Ollama returned {resp.status_code}"}}
    except Exception as e:
        return {"data": None, "error": {"message": str(e)}}

@router.post("/ollama/pull")
async def pull_ollama_model(user: dict = Depends(get_current_user)):
    # In a real app, check if user is admin
    base_url = settings.ollama_base_url.rstrip("/")
    model = settings.ollama_model
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(f"{base_url}/api/pull", json={"name": model, "stream": False})
            if resp.status_code == 200:
                return {"data": resp.json(), "error": None}
            else:
                return {"data": None, "error": {"message": f"Ollama returned {resp.status_code}"}}
    except Exception as e:
        return {"data": None, "error": {"message": str(e)}}
