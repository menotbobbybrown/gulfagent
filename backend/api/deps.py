"""
FastAPI shared dependencies: current user from Supabase JWT.
"""

from uuid import UUID

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, create_client

from config import get_settings

settings = get_settings()
bearer_scheme = HTTPBearer()


def get_supabase() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_key)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    supabase: Client = Depends(get_supabase),
) -> UUID:
    """
    Validate the Supabase JWT from Authorization header.
    Returns the authenticated user's UUID.
    """
    token = credentials.credentials
    try:
        response = supabase.auth.get_user(token)
        if not response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return UUID(response.user.id)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Could not validate credentials") from exc
