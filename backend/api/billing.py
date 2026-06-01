"""
T63–T66 — Stripe billing integration.
T63: POST /api/billing/setup — create Stripe products + prices
T64: POST /api/billing/checkout — create Stripe checkout session
T65: Stripe webhook handled in webhooks.py
T66: Subscription sync on webhook
"""

from __future__ import annotations

import logging
from uuid import UUID

import stripe
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user_id
from config import get_settings
from db.models import User
from db.session import get_db

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/billing", tags=["billing"])

stripe.api_key = settings.stripe_secret_key

# ──────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────

class SetupResponse(BaseModel):
    data: dict
    error: str | None = None


class CheckoutRequest(BaseModel):
    tier: str = "basic"  # "basic" | "pro"


class CheckoutResponse(BaseModel):
    data: dict
    error: str | None = None


# ──────────────────────────────────────────────
# T63 — POST /api/billing/setup
# ──────────────────────────────────────────────

@router.post("/setup", response_model=SetupResponse)
async def setup_stripe_products(user_id: UUID = Depends(get_current_user_id)) -> SetupResponse:
    """
    Create Stripe products for Basic (AED 150/mo) and Pro (AED 500/mo)
    if they don't already exist. Returns price IDs.
    Idempotent — safe to call multiple times.
    """
    try:
        # Look for existing products by name
        existing = stripe.Product.list(active=True, limit=50)
        products = {p.name: p for p in existing.data}

        results = {}

        for name, amount, metadata in [
            ("GulfAgent Basic", 15_000, {"tier": "basic", "credits": "5000", "tasks": "50"}),
            ("GulfAgent Pro", 50_000, {"tier": "pro", "credits": "20000", "tasks": "200"}),
        ]:
            if name in products:
                product = products[name]
            else:
                product = stripe.Product.create(
                    name=name,
                    description=f"GulfAgent {name.split()[-1]} plan — monthly subscription",
                    metadata=metadata,
                )

            # Check for existing active price
            prices = stripe.Price.list(
                product=product.id,
                active=True,
                limit=1,
                currency="aed",
            )
            if prices.data:
                price_id = prices.data[0].id
            else:
                price = stripe.Price.create(
                    product=product.id,
                    unit_amount=amount,
                    currency="aed",
                    recurring={"interval": "month"},
                    metadata=metadata,
                )
                price_id = price.id

            results[name.split()[-1].lower()] = {
                "product_id": product.id,
                "price_id": price_id,
                "amount_aed": amount / 100,
                "interval": "month",
            }

        logger.info("Stripe products synced: %s", results)
        return SetupResponse(data=results)

    except stripe.StripeError as e:
        logger.error("Stripe setup error: %s", e)
        raise HTTPException(status_code=500, detail={
            "code": "STRIPE_ERROR",
            "message": f"Failed to setup Stripe products: {str(e)}",
        })


# ──────────────────────────────────────────────
# T64 — POST /api/billing/checkout
# ──────────────────────────────────────────────

@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    body: CheckoutRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> CheckoutResponse:
    """
    Create a Stripe checkout session for the requested tier.
    On completion the user is redirected to /dashboard/billing/success
    or /dashboard/billing/cancel.
    """
    # Validate tier
    if body.tier not in ("basic", "pro"):
        raise HTTPException(status_code=400, detail={
            "code": "INVALID_TIER",
            "message": "Tier must be 'basic' or 'pro'.",
        })

    # Get user from DB
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail={
            "code": "USER_NOT_FOUND",
            "message": "User not found.",
        })

    # Determine price ID — prefer env var, else auto-detect from Stripe
    price_id = (
        settings.stripe_price_basic if body.tier == "basic"
        else settings.stripe_price_pro
    )

    if not price_id:
        # Auto-detect from Stripe by product metadata
        try:
            products = stripe.Product.list(active=True, limit=50)
            for p in products.data:
                if p.metadata.get("tier") == body.tier:
                    prices = stripe.Price.list(
                        product=p.id, active=True, limit=1, currency="aed"
                    )
                    if prices.data:
                        price_id = prices.data[0].id
                        break
        except stripe.StripeError as e:
            logger.error("Failed to auto-detect price: %s", e)

    if not price_id:
        raise HTTPException(status_code=500, detail={
            "code": "PRICE_NOT_FOUND",
            "message": "Could not find Stripe price for this tier. Run POST /api/billing/setup first.",
        })

    app_url = settings.next_public_app_url.rstrip("/")

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{app_url}/dashboard/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{app_url}/dashboard/billing/cancel",
            customer_email=user.email,
            client_reference_id=str(user_id),
            metadata={
                "user_id": str(user_id),
                "tier": body.tier,
            },
            subscription_data={
                "metadata": {
                    "user_id": str(user_id),
                    "tier": body.tier,
                },
            },
        )

        logger.info("Checkout session created: %s for user %s", session.id, user_id)
        return CheckoutResponse(data={
            "session_id": session.id,
            "url": session.url,
            "tier": body.tier,
        })

    except stripe.StripeError as e:
        logger.error("Stripe checkout error: %s", e)
        raise HTTPException(status_code=500, detail={
            "code": "STRIPE_CHECKOUT_ERROR",
            "message": f"Failed to create checkout session: {str(e)}",
        })


# ──────────────────────────────────────────────
# GET /api/billing/portal — Stripe customer portal
# ──────────────────────────────────────────────

@router.post("/portal")
async def customer_portal(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a Stripe Customer Portal session for managing subscription."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail={
            "code": "NO_SUBSCRIPTION",
            "message": "No active subscription found. Subscribe first.",
        })

    try:
        portal = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=f"{settings.next_public_app_url.rstrip('/')}/dashboard/settings",
        )
        return {"data": {"url": portal.url}, "error": None}
    except stripe.StripeError as e:
        raise HTTPException(status_code=500, detail={
            "code": "PORTAL_ERROR",
            "message": str(e),
        })