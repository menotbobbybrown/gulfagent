"""
BullMQ scheduler integration for GulfAgent.

Handles delayed jobs and recurring automations via BullMQ on Redis.
Used for:
  - T32: Auto-deny persistence for approval timeouts (delayed job)
  - Automations: cron-based recurring tasks (BullMQ repeatable jobs)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from config import get_settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# BullMQ queue names
# ──────────────────────────────────────────────

QUEUE_APPROVALS = "gulfagent:approvals"
QUEUE_AUTOMATIONS = "gulfagent:automations"

# ──────────────────────────────────────────────
# SchedulerAgent
# ──────────────────────────────────────────────

try:
    from bullmq import Queue, Worker, Job

    _BULLMQ_AVAILABLE = True
except ImportError:
    _BULLMQ_AVAILABLE = False
    logger.warning("bullmq not installed — scheduler agent unavailable")


class SchedulerAgent:
    """
    Wraps BullMQ queues for delayed and recurring task scheduling.

    Usage:
        scheduler = SchedulerAgent()
        await scheduler.start()

        # Schedule auto-deny after 5 minutes
        await scheduler.schedule_auto_deny(approval_id, task_id)

        # Schedule recurring automation
        await scheduler.schedule_automation(automation_id, cron)
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._approval_queue: Queue | None = None
        self._automation_queue: Queue | None = None
        self._worker: Worker | None = None
        self._started = False

    async def start(self) -> None:
        """Initialize BullMQ queues and start the worker."""
        if not _BULLMQ_AVAILABLE:
            logger.warning("BullMQ not available — scheduler not started")
            return

        if self._started:
            return

        redis_url = self.settings.redis_url

        self._approval_queue = Queue(QUEUE_APPROVALS, {"connection": {"url": redis_url}})
        self._automation_queue = Queue(QUEUE_AUTOMATIONS, {"connection": {"url": redis_url}})

        self._worker = Worker(
            QUEUE_APPROVALS,
            self._process_job,
            {"connection": {"url": redis_url}},
        )

        self._started = True
        logger.info("SchedulerAgent started — queues: %s, %s", QUEUE_APPROVALS, QUEUE_AUTOMATIONS)

    async def stop(self) -> None:
        """Gracefully shut down queues and worker."""
        if self._worker:
            await self._worker.close()
        if self._approval_queue:
            await self._approval_queue.close()
        if self._automation_queue:
            await self._automation_queue.close()
        self._started = False
        logger.info("SchedulerAgent stopped")

    async def schedule_auto_deny(
        self,
        approval_id: str,
        task_id: str,
        delay_seconds: int = 300,
    ) -> str | None:
        """
        Schedule an auto-deny job for an approval timeout.

        Returns the BullMQ job ID, or None if BullMQ is unavailable.
        """
        if not self._approval_queue:
            logger.warning("Approval queue not available — cannot schedule auto-deny")
            return None

        job = await self._approval_queue.add(
            "auto-deny",
            {"approval_id": approval_id, "task_id": task_id},
            {"delay": delay_seconds * 1000},  # BullMQ delay is in ms
        )
        logger.info(
            "Scheduled auto-deny for approval %s (job=%s, delay=%ds)",
            approval_id,
            job.id,
            delay_seconds,
        )
        return job.id

    async def schedule_automation(
        self,
        automation_id: str,
        user_id: str,
        prompt: str,
        cron: str,
    ) -> str | None:
        """
        Schedule a recurring automation via BullMQ repeatable job.

        Returns the BullMQ job ID, or None if BullMQ is unavailable.
        """
        if not self._automation_queue:
            logger.warning("Automation queue not available — cannot schedule")
            return None

        # Remove any existing repeatable job for this automation
        try:
            await self._automation_queue.removeRepeatableByKey(
                f"automation:{automation_id}"
            )
        except Exception:
            pass

        job = await self._automation_queue.add(
            f"automation:{automation_id}",
            {"automation_id": automation_id, "user_id": user_id, "prompt": prompt},
            {
                "repeat": {"pattern": cron},
                "jobId": f"automation:{automation_id}",
            },
        )
        logger.info(
            "Scheduled automation %s (job=%s, cron=%s)",
            automation_id,
            job.id,
            cron,
        )
        return job.id

    async def remove_automation(self, automation_id: str) -> None:
        """Remove a recurring automation job."""
        if not self._automation_queue:
            return
        try:
            await self._automation_queue.removeRepeatableByKey(
                f"automation:{automation_id}"
            )
            logger.info("Removed automation %s", automation_id)
        except Exception as e:
            logger.warning("Failed to remove automation %s: %s", automation_id, e)

    async def _process_job(self, job: Job) -> None:
        """
        Worker callback for approval queue jobs.
        Auto-denies approval if still pending.
        """
        data = job.data
        job_name = job.name or "unknown"
        logger.info("Processing scheduler job %s: %s", job.id, job_name)

        if job_name == "auto-deny":
            await self._handle_auto_deny(data.get("approval_id"), data.get("task_id"))

    async def _handle_auto_deny(self, approval_id: str | None, task_id: str | None) -> None:
        """T32: Mark approval as timed out if still undecided."""
        if not approval_id:
            return

        from db.session import AsyncSessionLocal
        from sqlalchemy import select, update
        from db.models import Approval

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
                logger.info("Auto-deny executed for approval %s", approval_id)

    async def cancel_auto_deny(self, approval_id: str) -> None:
        """Cancel a pending auto-deny job (e.g., user approved manually)."""
        if not self._approval_queue:
            return
        try:
            # BullMQ doesn't have a direct "cancel by job data" — we remove by jobId
            # Since we don't store job IDs, we skip this for now.
            pass
        except Exception:
            pass


# Module-level singleton
scheduler = SchedulerAgent()