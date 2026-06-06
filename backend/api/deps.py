"""
FastAPI shared dependencies: current user from Supabase JWT.

Supports two auth modes:
  1. Authorization: Bearer <token> header (standard)
  2. ?token=<token> query parameter (for SSE / EventSource)
"""

import asyncio
from uuid import UUID

from fastapi import Depends, HTTPException, Query, Security, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, create_client
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from db.session import get_db

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)


def get_language(request: Request) -> str:
    """Detect language from Accept-Language header."""
    accept_lang = request.headers.get("Accept-Language", "en")
    if "ar" in accept_lang.lower():
        return "ar"
    return "en"



def get_supabase() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_key)


def _validate_token_sync(supabase: Client, token: str) -> UUID:
    """Synchronous token validation — called via asyncio.to_thread."""
    response = supabase.auth.get_user(token)
    if not response or not response.user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return UUID(response.user.id)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    token: str | None = Query(None, description="Auth token as query param (SSE fallback)"),
    supabase: Client = Depends(get_supabase),
) -> UUID:
    """
    Validate the Supabase JWT from Authorization header (preferred)
    or ?token= query parameter (EventSource fallback).

    supabase-py uses synchronous httpx under the hood, so we wrap the
    blocking call in asyncio.to_thread() to avoid stalling the event loop.
    """
    # Resolve token from header or query param
    resolved_token: str | None = None
    if credentials and credentials.credentials:
        resolved_token = credentials.credentials
    elif token:
        resolved_token = token

    if not resolved_token:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication token. Provide Authorization header or ?token= query param.",
        )

    try:
        # Offload blocking supabase.auth.get_user() to a thread
        user_id: UUID = await asyncio.to_thread(
            _validate_token_sync, supabase, resolved_token
        )
        return user_id
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Could not validate credentials") from exc


async def get_current_admin(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> UUID:
    from fastapi import HTTPException
    from sqlalchemy import select
    from db.models import User
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user_id
