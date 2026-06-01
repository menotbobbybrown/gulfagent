"""
T27 — Approvals table already defined in db/models.py (Phase 1).
T28 — Before destructive actions: create approval record, pause agent.
T32 — Auto-deny after 5 min timeout (BullMQ delayed job for persistence).

Usage in agent code:
    from core.approval_manager import request_approval, ApprovalRequiredError
    await request_approval(session, task_id, action_type="email", payload={...})
    # Raises ApprovalRequiredError immediately — agent is paused.
    # Resume path: POST /api/approvals/{id}/decide → decision stored in DB.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Approval, Task, TaskStatus

logger = logging.getLogger(__name__)

APPROVAL_TIMEOUT_SECONDS = 300  # 5 minutes
POLL_INTERVAL_SECONDS = 2


class ApprovalRequiredError(Exception):
    """
    Raised by request_approval() to pause agent execution.
    Carry the approval_id so the caller can surface it to the user.
    """
    def __init__(self, approval_id: str, action_type: str):
        self.approval_id = approval_id
        self.action_type = action_type
        super().__init__(f"Approval required for action: {action_type} (approval_id={approval_id})")


class ApprovalDeniedError(Exception):
    """Raised when the user explicitly denies or the approval times out."""
    def __init__(self, reason: str = "denied"):
        self.reason = reason
        super().__init__(f"Action denied: {reason}")


async def request_approval(
    session: AsyncSession,
    task_id: str,
    action_type: str,
    payload: dict,
) -> None:
    """
    Create an approval record and update the task status to awaiting_approval.
    Then blocks (polls) until approved, denied, or timed out.

    action_type: one of  email | form_submit | payment | file_delete
    """
    expires_at = datetime.utcnow() + timedelta(seconds=APPROVAL_TIMEOUT_SECONDS)

    approval = Approval(
        task_id=UUID(task_id),
        action_type=action_type,
        action_payload=payload,
        expires_at=expires_at,
    )
    session.add(approval)

    await session.execute(
        update(Task)
        .where(Task.id == UUID(task_id))
        .values(status=TaskStatus.awaiting_approval)
    )
    await session.commit()
    await session.refresh(approval)

    approval_id = str(approval.id)
    logger.info(
        "Approval required: task=%s action=%s approval_id=%s expires=%s",
        task_id, action_type, approval_id, expires_at.isoformat()
    )

    # Schedule auto-deny via BullMQ for persistence across restarts
    try:
        from agents.scheduler_agent import scheduler
        await scheduler.schedule_auto_deny(
            approval_id=approval_id,
            task_id=task_id,
            delay_seconds=APPROVAL_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        logger.warning(
            "BullMQ auto-deny scheduling failed (%s), falling back to in-process timer",
            exc,
        )
        # Fallback: in-process timer
        asyncio.create_task(
            _auto_deny_after_timeout(approval_id, APPROVAL_TIMEOUT_SECONDS)
        )

    # Poll until decision
    deadline = datetime.utcnow() + timedelta(seconds=APPROVAL_TIMEOUT_SECONDS + 10)
    from db.session import AsyncSessionLocal

    while datetime.utcnow() < deadline:
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        async with AsyncSessionLocal() as poll_session:
            result = await poll_session.execute(
                select(Approval).where(Approval.id == UUID(approval_id))
            )
            rec = result.scalar_one_or_none()
            if rec and rec.decision:
                if rec.decision == "approved":
                    logger.info("Approval granted: %s", approval_id)
                    # Restore task to running
                    async with AsyncSessionLocal() as ts:
                        await ts.execute(
                            update(Task)
                            .where(Task.id == UUID(task_id))
                            .values(status=TaskStatus.running)
                        )
                        await ts.commit()
                    return
                else:
                    raise ApprovalDeniedError(rec.decision)

    # Timed out — deny
    raise ApprovalDeniedError("timeout")


async def _auto_deny_after_timeout(approval_id: str, timeout_seconds: int) -> None:
    """T32: Fallback background coroutine — auto-deny approval after timeout."""
    await asyncio.sleep(timeout_seconds)
    from db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Approval).where(Approval.id == UUID(approval_id))
        )
        rec = result.scalar_one_or_none()
        if rec and rec.decision is None:
            await session.execute(
                update(Approval)
                .where(Approval.id == UUID(approval_id))
                .values(decision="timeout", decided_at=datetime.utcnow())
            )
            await session.commit()
            logger.info("Approval auto-denied (timeout): %s", approval_id)


async def get_pending_approvals(session: AsyncSession, user_id: UUID) -> list[Approval]:
    """Return all open approvals for a user's tasks."""
    result = await session.execute(
        select(Approval)
        .join(Task, Task.id == Approval.task_id)
        .where(
            Task.user_id == user_id,
            Approval.decision.is_(None),
            Approval.expires_at > datetime.utcnow(),
        )
        .order_by(Approval.created_at.desc())
    )
    return list(result.scalars().all())


async def decide_approval(
    session: AsyncSession,
    approval_id: str,
    user_id: UUID,
    decision: str,  # "approved" | "denied"
) -> Approval:
    """Record the user's decision. Validates ownership."""
    result = await session.execute(
        select(Approval)
        .join(Task, Task.id == Approval.task_id)
        .where(Approval.id == UUID(approval_id), Task.user_id == user_id)
    )
    approval = result.scalar_one_or_none()
    if not approval:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Approval not found")

    if approval.decision is not None:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="Approval already decided")

    if approval.expires_at < datetime.utcnow():
        from fastapi import HTTPException
        raise HTTPException(status_code=410, detail="Approval has expired")

    await session.execute(
        update(Approval)
        .where(Approval.id == UUID(approval_id))
        .values(decision=decision, decided_at=datetime.utcnow())
    )
    await session.commit()
    await session.refresh(approval)
    logger.info("Approval decided: %s → %s", approval_id, decision)
    return approval
