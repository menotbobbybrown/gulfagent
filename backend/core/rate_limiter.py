from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
import base64, json

TIER_LIMITS = {"basic": "10/minute", "pro": "30/minute", "enterprise": "100/minute"}

def get_rate_limit_key(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth and auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1]
        try:
            payload = token.split(".")[1]
            padded = payload + "=" * (-len(payload) % 4)
            data = json.loads(base64.b64decode(padded))
            return f"user:{data.get('sub', 'anon')}"
        except Exception:
            return f"token:{token[-16:]}"
    return get_remote_address(request)

limiter = Limiter(key_func=get_rate_limit_key, default_limits=["60/minute"], enabled=True)