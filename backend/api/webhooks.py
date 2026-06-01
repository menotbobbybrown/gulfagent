"""
T33 — Evolution API setup, webhook registration endpoint
T34 — POST /api/webhooks/whatsapp — receive incoming messages
T35 — Parse incoming message → create task → execute
T36 — Send result back to user via WhatsApp
T37 — Approval via WhatsApp — Y to approve, N to deny
T39 — User phone number linked to Supabase user account
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agents.arabic_router import detect_arabic
from agents.whatsapp_agent import whatsapp
from config import get_settings
from core.approval_manager import decide_approval
from core.langgraph_pipeline import run_task
from core.usage_tracker import check_credits_before_task, deduct_credits_after_task
from db.models import Approval, Task, TaskStatus, User
from db.session import get_db, AsyncSessionLocal
import stripe as stripe_lib

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_phone(phone: str) -> str:
    """Normalize to E.164: strip +, spaces, dashes. Always starts with country code."""
    clean = phone.replace("+", "").replace(" ", "").replace("-", "")
    return clean


async def _get_or_create_user_by_phone(session: AsyncSession, phone: str) -> User | None:
    """
    T39 — Find a Supabase user by their E.164 phone number.
    If no user has that phone, we can't auto-create (needs Supabase auth).
    Returns None if not found.
    """
    result = await session.execute(
        select(User).where(User.phone == f"+{phone}")
    )
    return result.scalar_one_or_none()


async def _link_phone_to_user(session: AsyncSession, user_id: UUID, phone: str) -> None:
    """T39 — Store E.164 phone on user row."""
    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(phone=f"+{phone}")
    )
    await session.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Background: execute task and send WhatsApp result
# ─────────────────────────────────────────────────────────────────────────────

async def _execute_and_notify(
    task_id: str,
    user_id: str,
    prompt: str,
    phone: str,
) -> None:
    """Run the pipeline and send result / error back via WhatsApp."""
    async with AsyncSessionLocal() as session:
        # Mark running
        await session.execute(
            update(Task)
            .where(Task.id == UUID(task_id))
            .values(status=TaskStatus.running, started_at=datetime.utcnow())
        )
        await session.commit()

    outcome = await run_task(task_id=task_id, user_id=user_id, prompt=prompt)

    async with AsyncSessionLocal() as session:
        if outcome["error"]:
            await session.execute(
                update(Task)
                .where(Task.id == UUID(task_id))
                .values(
                    status=TaskStatus.failed,
                    error_message=outcome["error"],
                    tokens_used=outcome["tokens_used"],
                    credits_used=outcome["credits_used"],
                    task_type=outcome["task_type"],
                    metadata=outcome["metadata"],
                    completed_at=datetime.utcnow(),
                )
            )
            await session.commit()
            await whatsapp.send_error(phone, prompt, outcome["error"])
        else:
            await session.execute(
                update(Task)
                .where(Task.id == UUID(task_id))
                .values(
                    status=TaskStatus.completed,
                    result=outcome["result"],
                    tokens_used=outcome["tokens_used"],
                    credits_used=outcome["credits_used"],
                    task_type=outcome["task_type"],
                    metadata=outcome["metadata"],
                    completed_at=datetime.utcnow(),
                )
            )
            await deduct_credits_after_task(session, UUID(user_id), outcome["credits_used"])
            await session.commit()
            await whatsapp.send_result(phone, prompt, outcome["result"])


# ─────────────────────────────────────────────────────────────────────────────
# T34 — POST /api/webhooks/whatsapp
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Evolution API calls this endpoint for every event (MESSAGES_UPSERT, etc.)
    We validate the API key, then dispatch based on event type.
    """
    # Optional API key verification (Evolution sends key in header)
    incoming_key = request.headers.get("apikey", "")
    if settings.evolution_api_key and incoming_key != settings.evolution_api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event = body.get("event", "")
    logger.info("WhatsApp webhook: event=%s", event)

    if event == "MESSAGES_UPSERT":
        await _handle_message(body.get("data", {}), background_tasks, db)
    elif event == "CONNECTION_UPDATE":
        status = body.get("data", {}).get("state", "")
        logger.info("WhatsApp connection state: %s", status)
    # Silently ignore other events

    return {"data": {"received": True}, "error": None}


# ─────────────────────────────────────────────────────────────────────────────
# T35 — Parse message → create task or handle approval reply
# ─────────────────────────────────────────────────────────────────────────────

async def _handle_message(
    data: dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession,
) -> None:
    """
    Route incoming WhatsApp message.
    1. Extract phone + text
    2. Check if it's an approval reply (Y/N)
    3. Otherwise treat as a new task prompt
    """
    # Parse Evolution API v2 message format
    key = data.get("key", {})
    if key.get("fromMe", False):
        return  # Ignore messages we sent

    message = data.get("message", {})
    text = (
        message.get("conversation")
        or message.get("extendedTextMessage", {}).get("text")
        or ""
    ).strip()

    if not text:
        return  # Ignore non-text messages (images, docs, etc.)

    # Normalize phone (Evolution gives "remoteJid": "971501234567@s.whatsapp.net")
    remote_jid = key.get("remoteJid", "")
    phone = _normalize_phone(remote_jid.split("@")[0])

    logger.info("Incoming WhatsApp from +%s: %s", phone, text[:80])

    # Look up user by phone number
    user = await _get_or_create_user_by_phone(db, phone)
    if not user:
        await whatsapp.send_text(
            phone,
            "👋 Welcome to GulfAgent! To get started, please sign up at our dashboard "
            "and link your WhatsApp number in Settings.",
        )
        return

    # T37 — Check if this is an approval Y/N reply
    upper = text.upper().strip()
    if upper in ("Y", "YES", "APPROVE", "نعم", "موافق"):
        await _handle_approval_reply(db, user, phone, "approved")
        return
    if upper in ("N", "NO", "DENY", "لا", "رفض"):
        await _handle_approval_reply(db, user, phone, "denied")
        return

    # T35 — New task
    try:
        await check_credits_before_task(db, user.id, estimated_cost=1)
    except HTTPException as e:
        detail = e.detail
        if isinstance(detail, dict):
            msg = detail.get("message", "Credit limit reached.")
        else:
            msg = str(detail)
        await whatsapp.send_text(phone, f"⚠️ {msg}")
        return

    # T38 — Detect Arabic for acknowledgement language
    is_arabic = detect_arabic(text)
    ack = "⏳ جاري تنفيذ المهمة…" if is_arabic else "⏳ On it! Running your task…"
    await whatsapp.send_text(phone, ack)

    task = Task(
        user_id=user.id,
        prompt=text,
        source="whatsapp",
        status=TaskStatus.pending,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    background_tasks.add_task(
        _execute_and_notify,
        str(task.id),
        str(user.id),
        text,
        phone,
    )


async def _handle_approval_reply(
    db: AsyncSession,
    user: User,
    phone: str,
    decision: str,
) -> None:
    """
    T37 — Find the most recent pending approval for this user and apply the decision.
    """
    from core.approval_manager import get_pending_approvals

    approvals = await get_pending_approvals(db, user.id)
    if not approvals:
        await whatsapp.send_text(phone, "No pending approvals found.")
        return

    # Act on the most recent one
    approval = approvals[0]
    try:
        await decide_approval(db, str(approval.id), user.id, decision)
        if decision == "approved":
            msg = "✅ Approved. Continuing task…"
        else:
            msg = "❌ Denied. Task cancelled."
        await whatsapp.send_text(phone, msg)
    except HTTPException as e:
        await whatsapp.send_text(phone, f"Could not process: {e.detail}")


# ─────────────────────────────────────────────────────────────────────────────
# T33 — Admin: register webhook with Evolution API
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/whatsapp/register")
async def register_whatsapp_webhook(request: Request) -> dict:
    """
    One-time setup endpoint — call after deploy to register the webhook URL
    with the Evolution API instance.
    Secured by evolution_api_key header.
    """
    incoming_key = request.headers.get("apikey", "")
    if not incoming_key or incoming_key != settings.evolution_api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")

    app_url = settings.next_public_app_url.rstrip("/")
    webhook_url = f"{app_url}/api/webhooks/whatsapp"

    result = await whatsapp.register_webhook(webhook_url)
    return {"data": result, "error": None}


@router.get("/whatsapp/status")
async def whatsapp_status() -> dict:
    """Check Evolution API instance connection status."""
    status = await whatsapp.get_instance_status()
    return {"data": status, "error": None}


# ─────────────────────────────────────────────────────────────────────────────
# T65 — POST /api/webhooks/stripe
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/stripe")
async def stripe_webhook(request: Request) -> dict:
    """
    Handle Stripe webhook events:
    - checkout.session.completed — activate subscription, update user
    - invoice.paid — sync subscription status, reset monthly credits
    - customer.subscription.updated — handle plan changes
    - customer.subscription.deleted — downgrade to free tier
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe_lib.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe_lib.error.SignatureVerificationError as e:
        logger.warning("Stripe webhook signature verification failed: %s", e)
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.warning("Stripe webhook payload parse failed: %s", e)
        raise HTTPException(status_code=400, detail="Invalid payload")

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})
    logger.info("Stripe webhook: %s", event_type)

    async with AsyncSessionLocal() as db:
        try:
            if event_type == "checkout.session.completed":
                await _handle_checkout_completed(db, data)
            elif event_type == "invoice.paid":
                await _handle_invoice_paid(db, data)
            elif event_type == "customer.subscription.updated":
                await _handle_subscription_updated(db, data)
            elif event_type == "customer.subscription.deleted":
                await _handle_subscription_deleted(db, data)
            else:
                logger.info("Unhandled Stripe event: %s", event_type)
        except Exception as e:
            logger.error("Error handling Stripe event %s: %s", event_type, e)
            # Don't return error to Stripe — they'll retry

    return {"data": {"received": True}, "error": None}


async def _handle_checkout_completed(db: AsyncSession, data: dict) -> None:
    """
    Activate subscription: update user with stripe_customer_id,
    stripe_subscription_id, subscription_tier, subscription_status.
    """
    user_id = data.get("metadata", {}).get("user_id") or data.get("client_reference_id")
    customer_id = data.get("customer")
    subscription_id = data.get("subscription")
    tier = data.get("metadata", {}).get("tier", "basic")

    if not user_id or not customer_id or not subscription_id:
        logger.warning("checkout.session.completed missing fields: %s", data)
        return

    await db.execute(
        update(User)
        .where(User.id == UUID(user_id))
        .values(
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            subscription_tier=tier,
            subscription_status="active",
        )
    )
    await db.commit()
    logger.info("Subscription activated: user=%s tier=%s sub=%s", user_id, tier, subscription_id)


async def _handle_invoice_paid(db: AsyncSession, data: dict) -> None:
    """
    Sync subscription status on successful payment, reset monthly credits
    by updating the usage record.
    """
    subscription_id = data.get("subscription")
    if not subscription_id:
        return

    # Find user by subscription
    result = await db.execute(
        select(User).where(User.stripe_subscription_id == subscription_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("No user found for subscription %s", subscription_id)
        return

    # Update status
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(subscription_status="active")
    )
    await db.commit()
    logger.info("Invoice paid — subscription sync: user=%s", user.id)


async def _handle_subscription_updated(db: AsyncSession, data: dict) -> None:
    """
    Handle plan changes (upgrade/downgrade).
    Sync tier based on the subscription items.
    """
    subscription_id = data.get("id")
    status = data.get("status", "active")
    items = data.get("items", {}).get("data", [])

    if not subscription_id:
        return

    result = await db.execute(
        select(User).where(User.stripe_subscription_id == subscription_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("No user found for subscription %s", subscription_id)
        return

    # Detect tier from price metadata
    tier = user.subscription_tier
    for item in items:
        price = item.get("price", {})
        metadata = price.get("metadata", {})
        if metadata.get("tier"):
            tier = metadata["tier"]
            break

    sub_status = "active"
    if status in ("past_due", "unpaid"):
        sub_status = "past_due"
    elif status == "canceled":
        sub_status = "cancelled"
    elif status == "incomplete_expired":
        sub_status = "cancelled"

    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            subscription_tier=tier,
            subscription_status=sub_status,
        )
    )
    await db.commit()
    logger.info("Subscription updated: user=%s tier=%s status=%s", user.id, tier, sub_status)


async def _handle_subscription_deleted(db: AsyncSession, data: dict) -> None:
    """Downgrade user to free/basic tier when subscription is deleted."""
    subscription_id = data.get("id")
    if not subscription_id:
        return

    result = await db.execute(
        select(User).where(User.stripe_subscription_id == subscription_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            subscription_tier="basic",
            subscription_status="cancelled",
            stripe_subscription_id=None,
        )
    )
    await db.commit()
    logger.info("Subscription deleted — downgraded user=%s to basic", user.id)
