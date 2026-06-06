"""
GulfAgent — FastAPI application entry point.
T01: /health endpoint
T02: Supabase connection verified on startup
T73: Rate limiting with slowapi
T78: Sentry integration (commented out, opt-in)
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()

import sentry_sdk
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.1,
        environment="production",
    )
    logger.info("✓ Sentry initialized")

from api.tasks import router as tasks_router
from api.automations import router as automations_router
from api.skills import router as skills_router
from api.webhooks import router as webhooks_router
from api.billing import router as billing_router
from api.usage import router as usage_router
from api.approvals import router as approvals_router
from api.users import router as users_router
from api.admin import router as admin_router
from agents.scheduler_agent import scheduler
from core.rate_limiter import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware


# ──────────────────────────────────────────────
# Lifespan — startup / shutdown
# ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("GulfAgent backend starting…")

    # T02 — Verify Supabase connectivity on startup
    try:
        from supabase import create_client
        client = create_client(settings.supabase_url, settings.supabase_service_key)
        client.auth.admin.list_users()
        logger.info("✓ Supabase connection OK")
    except Exception as exc:
        logger.warning("Supabase connection check failed (non-fatal in dev): %s", exc)

    # Start BullMQ scheduler
    try:
        await scheduler.start()
        logger.info("✓ Scheduler started")
    except Exception as exc:
        logger.warning("Scheduler start failed (non-fatal): %s", exc)

    # Auto-seed skills
    try:
        from db.seed_skills import seed_skills
        from db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            await seed_skills(db)
        logger.info("✓ Skills seeded")
    except Exception as exc:
        logger.warning("Skill seeding failed (non-fatal): %s", exc)

    # M1 — Auto-register WhatsApp webhook
    try:
        if settings.evolution_api_url and settings.evolution_api_key:
            from agents.whatsapp_agent import whatsapp
            base_url = (settings.backend_url or settings.next_public_app_url).rstrip("/")
            webhook_url = f"{base_url}/api/webhooks/whatsapp"
            await whatsapp.register_webhook(webhook_url)
            logger.info("✓ WhatsApp webhook registered")

        # Check Evolution API connection health
        try:
            if settings.evolution_api_url and settings.evolution_api_key:
                from agents.whatsapp_agent import whatsapp
                status = await whatsapp.get_instance_status()
                if status.get("error"):
                    logger.warning("⚠ WhatsApp instance not connected: %s", status["error"])
                else:
                    logger.info("✓ WhatsApp instance connected")
        except Exception as exc:
            logger.warning("WhatsApp health check failed: %s", exc)
    except Exception as exc:
        logger.warning("WhatsApp webhook registration failed (non-fatal): %s", exc)

    yield

    try:
        await scheduler.stop()
        logger.info("Scheduler stopped")
    except Exception:
        pass
    logger.info("GulfAgent backend shutting down.")


# ──────────────────────────────────────────────
# App
# ──────────────────────────────────────────────

app = FastAPI(
    title="GulfAgent API",
    description="AI agent platform for GCC businesses",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# T73 — Rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        settings.next_public_app_url,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# Global error handler — structured { error } envelope
# ──────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={
            "data": None,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred.",
            },
        },
    )


# ──────────────────────────────────────────────
# Routers
# ──────────────────────────────────────────────

app.include_router(tasks_router)
app.include_router(automations_router)
app.include_router(skills_router)
app.include_router(webhooks_router)
app.include_router(billing_router)
app.include_router(usage_router)
app.include_router(approvals_router)
app.include_router(users_router)
app.include_router(admin_router)



# ──────────────────────────────────────────────
# T01 — Health endpoint
# ──────────────────────────────────────────────

@app.get("/health", tags=["system"])
async def health() -> dict:
    return {
        "data": {
            "status": "ok",
            "service": "gulfagent-api",
            "version": "0.1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
        "error": None,
    }


@app.get("/", tags=["system"])
async def root() -> dict:
    return {"data": {"message": "GulfAgent API — /docs for Swagger"}, "error": None}
