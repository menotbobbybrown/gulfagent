"""
T08 — LangGraph pipeline (Phase 1 simple LLM)
T24 — Add browser tool to pipeline
T25 — LLM-based task type classifier (replaces keyword heuristic)
Migrated to OpenRouter orchestrator.
Simplified to use ManagerAgent for all task types.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Literal
from uuid import UUID

from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from config import get_settings
from core.model_orchestrator import orchestrator
from db.models import User
from db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)
settings = get_settings()


# ──────────────────────────────────────────────
# State
# ──────────────────────────────────────────────

class AgentState(TypedDict):
    task_id: str
    user_id: str
    user_tier: str
    prompt: str
    task_type: str
    messages: Annotated[list, add_messages]
    result: str
    tokens_used: int
    credits_used: int
    error: str | None
    metadata: dict[str, Any]


# ──────────────────────────────────────────────
# T25 — LLM-based classifier
# ──────────────────────────────────────────────

async def classify_task(state: AgentState) -> AgentState:
    """
    Use Orchestrator to classify the task.
    """
    prompt = state["prompt"]
    metadata = state.get("metadata", {})
    language = metadata.get("language", "en")

    # Connector pre-screen
    connector_map = {
        "careem": "connector_careem",
        "noon": "connector_noon",
        "talabat": "connector_talabat",
        "dubai now": "connector_dubai_now",
        "dubainow": "connector_dubai_now"
    }

    pl = prompt.lower()
    for kw, task_type in connector_map.items():
        if kw in pl:
            return {**state, "task_type": task_type, "metadata": metadata}

    try:
        task_type = await orchestrator.classify(prompt, language)
    except Exception as e:
        logger.warning("Classifier LLM call failed (%s), defaulting to simple_qa", e)
        task_type = "simple_qa"

    return {**state, "task_type": task_type, "metadata": metadata}


# ──────────────────────────────────────────────
# ManagerAgent — delegates all tasks
# ──────────────────────────────────────────────

async def execute_manager(state: AgentState) -> AgentState:
    """Delegate to ManagerAgent for all task types."""
    from core.agent_manager import manager
    return await manager.run(state)


# ──────────────────────────────────────────────
# Router
# ──────────────────────────────────────────────

def route_by_type(state: AgentState) -> Literal["execute_manager"]:
    return "execute_manager"


# ──────────────────────────────────────────────
# Build graph
# ──────────────────────────────────────────────

def _build_graph() -> Any:
    builder = StateGraph(AgentState)

    builder.add_node("classify", classify_task)
    builder.add_node("execute_manager", execute_manager)

    builder.set_entry_point("classify")
    builder.add_edge("classify", "execute_manager")
    builder.add_edge("execute_manager", END)

    return builder.compile()


# Singleton
pipeline = _build_graph()


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

async def run_task(
    task_id: str,
    user_id: str,
    prompt: str,
) -> dict[str, Any]:
    """
    Execute a task through the LangGraph pipeline.
    Returns dict with: result, task_type, tokens_used, credits_used, error, metadata
    """
    # Fetch user tier
    user_tier = "basic"
    language = "en"
    try:
        async with AsyncSessionLocal() as db:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            user = await db.get(User, user_uuid)
            if user:
                user_tier = user.subscription_tier or "basic"
                language = user.preferred_language or "en"
    except Exception as e:
        logger.warning("Failed to fetch user tier for %s: %s", user_id, e)

    initial_state: AgentState = {
        "task_id": task_id,
        "user_id": user_id,
        "user_tier": user_tier,
        "prompt": prompt,
        "task_type": "simple_qa",
        "messages": [],
        "result": "",
        "tokens_used": 0,
        "credits_used": 0,
        "error": None,
        "metadata": {"language": language},
    }

    try:
        final_state = await pipeline.ainvoke(initial_state)
        return {
            "result": final_state.get("result", ""),
            "task_type": final_state.get("task_type", "simple_qa"),
            "tokens_used": final_state.get("tokens_used", 0),
            "credits_used": final_state.get("credits_used", 1),
            "error": final_state.get("error"),
            "metadata": final_state.get("metadata", {}),
        }
    except Exception as exc:
        logger.exception("Pipeline failed for task %s", task_id)
        return {
            "result": "",
            "task_type": "simple_qa",
            "tokens_used": 0,
            "credits_used": 1,
            "error": str(exc),
            "metadata": {},
        }