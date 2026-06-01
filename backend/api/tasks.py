"""
T05 — POST /api/tasks
T06 — GET /api/tasks/{id}
T07 — GET /api/tasks (paginated)
T17 — GET /api/tasks/stream (SSE live updates)
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user_id
from core.langgraph_pipeline import run_task
from core.usage_tracker import check_credits_before_task, deduct_credits_after_task
from db.models import Task, TaskStatus
from db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# ──────────────────────────────────────────────
# Pydantic schemas
# ──────────────────────────────────────────────

class TaskCreate(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10_000)
    source: str = Field(default="dashboard")


class TaskResponse(BaseModel):
    id: str
    user_id: str
    prompt: str
    task_type: str
    status: str
    result: str | None
    error_message: str | None
    tokens_used: int
    credits_used: int
    metadata: dict[str, Any]
    source: str
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class PaginatedTasks(BaseModel):
    data: list[TaskResponse]
    meta: dict[str, Any]
    error: None = None


class SingleTask(BaseModel):
    data: TaskResponse
    error: None = None


# ──────────────────────────────────────────────
# Background task runner
# ──────────────────────────────────────────────

async def _execute_task_bg(task_id: str, user_id: str, prompt: str) -> None:
    """Run the LangGraph pipeline and update the task record."""
    from db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        # Mark as running
        await session.execute(
            update(Task)
            .where(Task.id == UUID(task_id))
            .values(status=TaskStatus.running, started_at=datetime.utcnow())
        )
        await session.commit()

        outcome = await run_task(task_id=task_id, user_id=user_id, prompt=prompt)

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
            # Deduct credits after success
            await deduct_credits_after_task(session, UUID(user_id), outcome["credits_used"])

        await session.commit()
        logger.info("Task %s finished with status=%s", task_id, "completed" if not outcome["error"] else "failed")


# ──────────────────────────────────────────────
# POST /api/tasks — T05
# ──────────────────────────────────────────────

@router.post("", response_model=SingleTask, status_code=202)
async def create_task(
    body: TaskCreate,
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> SingleTask:
    # Check credits BEFORE creating task
    await check_credits_before_task(db, user_id, estimated_cost=1)

    task = Task(
        user_id=user_id,
        prompt=body.prompt,
        source=body.source,
        status=TaskStatus.pending,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # Queue background execution
    background_tasks.add_task(
        _execute_task_bg,
        str(task.id),
        str(user_id),
        body.prompt,
    )

    return SingleTask(data=TaskResponse.model_validate(task))


# ──────────────────────────────────────────────
# GET /api/tasks/stream — T17 (must be before /{id})
# ──────────────────────────────────────────────

@router.get("/stream")
async def stream_tasks(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    SSE endpoint. Pushes task status updates to connected clients.
    Client connects once; server pushes events as tasks change state.
    """

    async def event_generator():
        # Send initial snapshot of last 20 tasks
        result = await db.execute(
            select(Task)
            .where(Task.user_id == user_id)
            .order_by(desc(Task.created_at))
            .limit(20)
        )
        tasks = result.scalars().all()
        snapshot = [TaskResponse.model_validate(t).model_dump(mode="json") for t in tasks]
        yield f"event: snapshot\ndata: {json.dumps(snapshot)}\n\n"

        # Poll for running tasks every 2 seconds
        seen_statuses: dict[str, str] = {str(t.id): t.status for t in tasks}
        poll_errors = 0

        while True:
            await asyncio.sleep(2)
            try:
                from db.session import AsyncSessionLocal

                async with AsyncSessionLocal() as poll_session:
                    res = await poll_session.execute(
                        select(Task)
                        .where(Task.user_id == user_id)
                        .order_by(desc(Task.created_at))
                        .limit(50)
                    )
                    current = res.scalars().all()

                for t in current:
                    tid = str(t.id)
                    if seen_statuses.get(tid) != t.status:
                        seen_statuses[tid] = t.status
                        event_data = TaskResponse.model_validate(t).model_dump(mode="json")
                        yield f"event: task_update\ndata: {json.dumps(event_data)}\n\n"

                poll_errors = 0
            except asyncio.CancelledError:
                break
            except Exception as exc:
                poll_errors += 1
                logger.warning("SSE poll error #%d: %s", poll_errors, exc)
                if poll_errors >= 5:
                    yield f"event: error\ndata: {json.dumps({'message': 'Stream error'})}\n\n"
                    break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ──────────────────────────────────────────────
# GET /api/tasks/{id} — T06
# ──────────────────────────────────────────────

@router.get("/{task_id}", response_model=SingleTask)
async def get_task(
    task_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> SingleTask:
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return SingleTask(data=TaskResponse.model_validate(task))


# ──────────────────────────────────────────────
# GET /api/tasks — T07
# ──────────────────────────────────────────────

@router.get("", response_model=PaginatedTasks)
async def list_tasks(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    automation_id: UUID | None = Query(default=None),
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> PaginatedTasks:
    offset = (page - 1) * limit
    query = select(Task).where(Task.user_id == user_id)
    if status:
        query = query.where(Task.status == status)
    if automation_id:
        query = query.where(Task.automation_id == automation_id)
    query = query.order_by(desc(Task.created_at)).offset(offset).limit(limit)

    result = await db.execute(query)
    tasks = result.scalars().all()

    # Count total
    from sqlalchemy import func
    count_q = select(func.count()).select_from(Task).where(Task.user_id == user_id)
    if status:
        count_q = count_q.where(Task.status == status)
    if automation_id:
        count_q = count_q.where(Task.automation_id == automation_id)
    total_result = await db.execute(count_q)
    total = total_result.scalar_one()

    return PaginatedTasks(
        data=[TaskResponse.model_validate(t) for t in tasks],
        meta={
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        },
    )
