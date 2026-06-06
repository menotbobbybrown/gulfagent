from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

TIER_LIMITS = {"basic": "10/minute", "pro": "30/minute", "enterprise": "100/minute"}

def get_rate_limit_key(request: Request) -> str:
    # Extract user ID from auth header for tier-based limits
    auth = request.headers.get("Authorization", "")
    if auth:
        return f"user:{auth[-20:]}"
    return get_remote_address(request)

limiter = Limiter(key_func=get_rate_limit_key, default_limits=["60/minute"], enabled=True)
