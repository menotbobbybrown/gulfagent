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
from datetime import datetime
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
        self._approval_worker: Worker | None = None
        self._automation_worker: Worker | None = None
        self._started = False

    async def start(self) -> None:
        """Initialize BullMQ queues and start workers."""
        if not _BULLMQ_AVAILABLE:
            logger.warning("BullMQ not available — scheduler not started")
            return

        if self._started:
            return

        redis_url = self.settings.redis_url

        self._approval_queue = Queue(QUEUE_APPROVALS, {"connection": {"url": redis_url}})
        self._automation_queue = Queue(QUEUE_AUTOMATIONS, {"connection": {"url": redis_url}})

        # Worker for approvals (auto-deny)
        self._approval_worker = Worker(
            QUEUE_APPROVALS,
            self._process_approval_job,
            {"connection": {"url": redis_url}},
        )

        # Worker for automations
        self._automation_worker = Worker(
            QUEUE_AUTOMATIONS,
            self._process_automation_job,
            {"connection": {"url": redis_url}},
        )

        self._started = True
        logger.info("SchedulerAgent started — queues: %s, %s", QUEUE_APPROVALS, QUEUE_AUTOMATIONS)
        
        # B5 — Restore active automations on startup
        try:
            await self.restore_automations()
        except Exception as e:
            logger.error("Failed to restore automations: %s", e)

    async def restore_automations(self) -> None:
        """Query DB for active automations and re-register them with BullMQ."""
        from db.session import AsyncSessionLocal
        from db.models import Automation
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Automation).where(Automation.active == True)
            )
            active_automations = result.scalars().all()
            
            count = 0
            for auto in active_automations:
                await self.schedule_automation(
                    automation_id=str(auto.id),
                    user_id=str(auto.user_id),
                    prompt=auto.prompt,
                    cron=auto.cron
                )
                count += 1
            
            logger.info("Restored %d active automations from database", count)

    async def stop(self) -> None:
        """Gracefully shut down queues and workers."""
        if self._approval_worker:
            await self._approval_worker.close()
        if self._automation_worker:
            await self._automation_worker.close()
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
            # For repeatable jobs, we need to know the pattern and name to remove it
            # But we can also try to remove by key if we have it.
            # In bullmq-python, it's often better to just add with same jobId/repeat key
            # but let's try to be clean.
            pass
        except Exception:
            pass

        job = await self._automation_queue.add(
            f"automation:{automation_id}",
            {"automation_id": automation_id, "user_id": user_id, "prompt": prompt},
            {
                "repeat": {"pattern": cron},
                "jobId": f"automation:{automation_id}",
                "removeOnComplete": True,
                "removeOnFail": False,
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
            # In bullmq-python, removing repeatable jobs can be tricky without the exact repeat options
            # A common way is to use a specific job name or ID.
            # Here we try to remove it using the repeatable job key if we can find it.
            # Since we don't store the key, we'll try to find it by name.
            repeatables = await self._automation_queue.getRepeatableJobs()
            for r in repeatables:
                if r['name'] == f"automation:{automation_id}":
                    await self._automation_queue.removeRepeatableByKey(r['key'])
                    logger.info("Removed automation %s (key=%s)", automation_id, r['key'])
        except Exception as e:
            logger.warning("Failed to remove automation %s: %s", automation_id, e)

    async def _process_approval_job(self, job: Job) -> None:
        """Worker callback for approval queue jobs."""
        data = job.data
        job_name = job.name or "unknown"
        logger.info("Processing approval job %s: %s", job.id, job_name)

        if job_name == "auto-deny":
            await self._handle_auto_deny(data.get("approval_id"), data.get("task_id"))

    async def _process_automation_job(self, job: Job) -> None:
        """Worker callback for automation queue jobs."""
        data = job.data
        automation_id = data.get("automation_id")
        user_id = data.get("user_id")
        prompt = data.get("prompt")

        if not all([automation_id, user_id, prompt]):
            logger.warning("Missing data in automation job %s", job.id)
            return

        logger.info("Running automation %s for user %s", automation_id, user_id)

        from db.session import AsyncSessionLocal
        from db.models import Task, TaskStatus, Automation, User
        from core.langgraph_pipeline import run_task
        from agents.whatsapp_agent import whatsapp
        from sqlalchemy import select, update
        from core.usage_tracker import deduct_credits_after_task

        async with AsyncSessionLocal() as session:
            # 1. Update automation last_run
            now = datetime.utcnow()
            await session.execute(
                update(Automation)
                .where(Automation.id == UUID(automation_id))
                .values(last_run=now)
            )
            await session.commit()

            # 2. Create Task record
            task = Task(
                user_id=UUID(user_id),
                prompt=prompt,
                source="automation",
                automation_id=UUID(automation_id),
                status=TaskStatus.pending
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)

            # 3. Mark as running
            await session.execute(
                update(Task)
                .where(Task.id == task.id)
                .values(status=TaskStatus.running, started_at=datetime.utcnow())
            )
            await session.commit()

            # 4. Run through LangGraph pipeline
            try:
                outcome = await run_task(task_id=str(task.id), user_id=user_id, prompt=prompt)
                
                # 5. Update Task result
                if outcome["error"]:
                    await session.execute(
                        update(Task)
                        .where(Task.id == task.id)
                        .values(
                            status=TaskStatus.failed,
                            error_message=outcome["error"],
                            tokens_used=outcome.get("tokens_used", 0),
                            credits_used=outcome.get("credits_used", 0),
                            task_type=outcome.get("task_type", "simple"),
                            metadata=outcome.get("metadata", {}),
                            completed_at=datetime.utcnow(),
                        )
                    )
                else:
                    await session.execute(
                        update(Task)
                        .where(Task.id == task.id)
                        .values(
                            status=TaskStatus.completed,
                            result=outcome["result"],
                            tokens_used=outcome.get("tokens_used", 0),
                            credits_used=outcome.get("credits_used", 0),
                            task_type=outcome.get("task_type", "simple"),
                            metadata=outcome.get("metadata", {}),
                            completed_at=datetime.utcnow(),
                        )
                    )
                    # Deduct credits
                    await deduct_credits_after_task(session, UUID(user_id), outcome.get("credits_used", 0))

                await session.commit()

                # 6. Send result via WhatsApp if user has phone linked
                user_res = await session.execute(select(User).where(User.id == UUID(user_id)))
                user = user_res.scalar_one_or_none()
                if user and user.phone:
                    try:
                        if outcome["error"]:
                            await whatsapp.send_error(user.phone, prompt, outcome["error"])
                        else:
                            await whatsapp.send_result(user.phone, prompt, outcome["result"])
                    except Exception as wa_err:
                        logger.error("Failed to send WhatsApp result for automation %s: %s", automation_id, wa_err)

            except Exception as e:
                logger.error("Error executing automation %s: %s", automation_id, e)
                await session.execute(
                    update(Task)
                    .where(Task.id == task.id)
                    .values(
                        status=TaskStatus.failed,
                        error_message=str(e),
                        completed_at=datetime.utcnow(),
                    )
                )
                await session.commit()

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
        """Cancel a pending auto-deny job."""
        if not self._approval_queue:
            return
        try:
            # BullMQ doesn't have a direct "cancel by job data" — we remove by jobId
            # This would require us to store the jobId when scheduling.
            pass
        except Exception:
            pass


# Module-level singleton
scheduler = SchedulerAgent()
