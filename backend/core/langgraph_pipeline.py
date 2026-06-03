"""
T08 — LangGraph pipeline (Phase 1 simple LLM)
T24 — Add browser tool to pipeline
T25 — LLM-based task type classifier (replaces keyword heuristic)
Migrated to OpenRouter orchestrator.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Literal
from uuid import UUID

from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict
from sqlalchemy import select

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
# Simple LLM node
# ──────────────────────────────────────────────

async def execute_simple_llm(state: AgentState) -> AgentState:
    """Route to OpenRouter orchestrator."""
    try:
        res = await orchestrator.run(
            task_type=state["task_type"],
            prompt=state["prompt"],
            user_tier=state.get("user_tier", "basic"),
            task_id=state["task_id"]
        )
        
        if res["error"]:
            return {**state, "result": "", "error": res["error"]}

        tokens = res["input_tokens"] + res["output_tokens"]
        credits = max(1, tokens // 100)
        
        return {
            **state,
            "result": res["result"],
            "tokens_used": tokens,
            "credits_used": credits,
            "error": None,
            "metadata": {
                **state.get("metadata", {}), 
                "model": res["model_used"],
                "cost_usd": res["cost_usd"],
                "latency_ms": res["latency_ms"],
                "fallback_used": res["fallback_used"]
            },
        }
    except Exception as e:
        logger.exception("Simple LLM node failed for task %s", state["task_id"])
        return {**state, "result": "", "error": str(e)}


# ──────────────────────────────────────────────
# T24 — Browser node (real browser-use execution)
# ──────────────────────────────────────────────

async def execute_browser(state: AgentState) -> AgentState:
    """
    T24: Run the browser agent, upload screenshots, return structured result.
    On failure falls back to simple LLM with a note.
    """
    from agents.browser_agent import BrowserAgent
    from agents.screenshot_storage import upload_screenshots

    agent = BrowserAgent(
        task_id=state["task_id"],
        user_id=state["user_id"],
        user_tier=state.get("user_tier", "basic"),
        headless=True,
        timeout_seconds=300,
    )

    try:
        browser_result = await agent.run(state["prompt"])

        # Build steps payload for metadata
        steps_data = [
            {
                "step_number": s.step_number,
                "action": s.action,
                "description": s.description,
                "url": s.url,
                "screenshot_path": s.screenshot_path,
                "screenshot_url": "",  # filled after upload
            }
            for s in browser_result.steps
        ]

        # Upload screenshots to Supabase Storage
        local_paths = [s.screenshot_path for s in browser_result.steps if s.screenshot_path]
        screenshot_urls: list[str] = []
        if local_paths:
            try:
                screenshot_urls = await upload_screenshots(
                    task_id=state["task_id"],
                    user_id=state["user_id"],
                    screenshot_paths=local_paths,
                )
                for i, step in enumerate(steps_data):
                    if i < len(screenshot_urls):
                        step["screenshot_url"] = screenshot_urls[i]
            except Exception as upload_err:
                logger.warning("Screenshot upload failed: %s", upload_err)

        metadata = {
            **state.get("metadata", {}),
            "steps": steps_data,
            "screenshots": screenshot_urls,
            "browser_success": browser_result.success,
        }

        if browser_result.success:
            return {
                **state,
                "result": browser_result.result,
                "credits_used": browser_result.credits_used,
                "error": None,
                "metadata": metadata,
            }
        else:
            # Browser failed — fall back to LLM
            logger.warning(
                "Browser agent failed for task %s (%s), falling back to LLM",
                state["task_id"],
                browser_result.error,
            )
            fallback = await execute_simple_llm({
                **state,
                "metadata": {**metadata, "browser_error": browser_result.error},
            })
            return {
                **fallback,
                "result": f"[Browser unavailable: {browser_result.error}]\n\n{fallback['result']}",
                "metadata": {**fallback.get("metadata", {}), **metadata},
            }
    finally:
        agent.cleanup()


async def execute_connector(state: AgentState) -> AgentState:
    """Execute specialized GCC connectors (Careem, Noon, Talabat, DubaiNow)."""
    from connectors import CareemConnector, NoonConnector, TalabatConnector, DubaiNowConnector
    
    task_type = state["task_type"]
    prompt = state["prompt"]
    task_id = state["task_id"]
    user_id = state["user_id"]
    user_tier = state.get("user_tier", "basic")
    
    connector_classes = {
        "connector_careem": CareemConnector,
        "connector_noon": NoonConnector,
        "connector_talabat": TalabatConnector,
        "connector_dubai_now": DubaiNowConnector,
    }
    
    cls = connector_classes.get(task_type)
    if not cls:
        return {**state, "error": f"Unknown connector: {task_type}"}
        
    connector = cls(task_id=task_id, user_id=user_id)
    try:
        # Most connectors will use the browser internally via BrowserAgent
        res = await connector.run(prompt)
        if res.get("error"):
            return {**state, "error": res["error"]}
            
        data = res.get("data", {})
        # Format the structured data into a human-readable response using LLM
        format_prompt = f"Format the following structured data into a helpful response for the user:\n\n{data}\n\nUser original request: {prompt}"
        
        format_res = await orchestrator.run("connector_format", format_prompt, user_tier=user_tier)
        
        tokens = format_res["input_tokens"] + format_res["output_tokens"]
        
        return {
            **state,
            "result": format_res["result"],
            "tokens_used": tokens,
            "credits_used": 50, # Connectors have a base cost
            "metadata": {
                **state.get("metadata", {}), 
                "connector_data": data, 
                "model": format_res["model_used"],
                "cost_usd": format_res["cost_usd"]
            }
        }
    except Exception as e:
        logger.exception("Connector %s failed", task_type)
        return {**state, "error": str(e)}


# ──────────────────────────────────────────────
# Router
# ──────────────────────────────────────────────

def route_by_type(state: AgentState) -> Literal["execute_simple", "execute_browser", "execute_connector"]:
    tt = state.get("task_type", "simple_qa")
    if tt.startswith("connector_"):
        return "execute_connector"
    if tt == "browser_task":
        return "execute_browser"
    return "execute_simple"


# ──────────────────────────────────────────────
# Build graph
# ──────────────────────────────────────────────

def _build_graph() -> Any:
    builder = StateGraph(AgentState)

    builder.add_node("classify", classify_task)
    builder.add_node("execute_simple", execute_simple_llm)
    builder.add_node("execute_browser", execute_browser)
    builder.add_node("execute_connector", execute_connector)

    builder.set_entry_point("classify")
    builder.add_conditional_edges(
        "classify",
        route_by_type,
        {
            "execute_simple": "execute_simple",
            "execute_browser": "execute_browser",
            "execute_connector": "execute_connector",
        },
    )
    builder.add_edge("execute_simple", END)
    builder.add_edge("execute_browser", END)
    builder.add_edge("execute_connector", END)


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
