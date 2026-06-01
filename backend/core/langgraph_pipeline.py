"""
T08 — LangGraph pipeline (Phase 1 simple LLM)
T24 — Add browser tool to pipeline
T25 — LLM-based task type classifier (replaces keyword heuristic)
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Literal
from uuid import UUID

import anthropic
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ──────────────────────────────────────────────
# State
# ──────────────────────────────────────────────

class AgentState(TypedDict):
    task_id: str
    user_id: str
    prompt: str
    task_type: Literal["simple", "browser", "whatsapp", "automation"]
    messages: Annotated[list, add_messages]
    result: str
    tokens_used: int
    credits_used: int
    error: str | None
    metadata: dict[str, Any]


# ──────────────────────────────────────────────
# T25 — LLM-based classifier
# ──────────────────────────────────────────────

_CLASSIFY_PROMPT = """\
You are a task router for an AI agent platform. Classify the user task below.

Respond with EXACTLY one word — either "browser" or "simple":

- "browser": requires loading websites, form interaction, web scraping, \
price monitoring, taking screenshots, logging into services, or any task \
that explicitly involves navigating the web.
- "simple": everything else — research from knowledge, text drafting, \
analysis, calculation, summarisation, code writing, Q&A.

User task: {prompt}

Classification:"""


async def classify_task(state: AgentState) -> AgentState:
    """
    T25: Use Claude to classify whether the task needs a browser.
    Fast single-token response (max_tokens=5).
    Falls back to keyword heuristic if API call fails.
    """
    prompt = state["prompt"]

    # Fast keyword pre-screen to avoid LLM call for obvious cases
    simple_keywords = ["draft", "write", "summarise", "summarize", "explain",
                       "calculate", "translate", "list", "compare", "analyse", "analyze"]
    browser_keywords = ["browse", "website", "url", "http", "scrape", "monitor price",
                        "fill form", "log in", "login", "check on noon", "check on amazon",
                        "navigate to", "open the", "go to the", "find on", "search on"]

    pl = prompt.lower()
    if any(kw in pl for kw in browser_keywords):
        return {**state, "task_type": "browser"}
    if any(kw in pl for kw in simple_keywords):
        return {**state, "task_type": "simple"}

    # LLM classification
    try:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        resp = await client.messages.create(
            model="claude-haiku-4-5-20251001",   # cheapest/fastest for classification
            max_tokens=5,
            messages=[{
                "role": "user",
                "content": _CLASSIFY_PROMPT.format(prompt=prompt[:500]),
            }],
        )
        answer = resp.content[0].text.strip().lower() if resp.content else "simple"
        task_type: Literal["simple", "browser"] = "browser" if "browser" in answer else "simple"
    except Exception as e:
        logger.warning("Classifier LLM call failed (%s), defaulting to simple", e)
        task_type = "simple"

    return {**state, "task_type": task_type}


# ──────────────────────────────────────────────
# Simple LLM node (routes through Arabic detector)
# ──────────────────────────────────────────────

async def execute_simple_llm(state: AgentState) -> AgentState:
    """Route to Claude or Qwen3 based on language detection."""
    from agents.arabic_router import route_to_llm

    try:
        result_text, tokens, model_used = await route_to_llm(state["prompt"])
        credits = max(1, tokens // 100)
        return {
            **state,
            "result": result_text,
            "tokens_used": tokens,
            "credits_used": credits,
            "error": None,
            "metadata": {**state.get("metadata", {}), "model": model_used},
        }
    except anthropic.APIError as e:
        logger.error("Anthropic API error: %s", e)
        return {**state, "result": "", "error": str(e)}
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


# ──────────────────────────────────────────────
# Router
# ──────────────────────────────────────────────

def route_by_type(state: AgentState) -> Literal["execute_simple", "execute_browser"]:
    return "execute_browser" if state.get("task_type") == "browser" else "execute_simple"


# ──────────────────────────────────────────────
# Build graph
# ──────────────────────────────────────────────

def _build_graph() -> Any:
    builder = StateGraph(AgentState)

    builder.add_node("classify", classify_task)
    builder.add_node("execute_simple", execute_simple_llm)
    builder.add_node("execute_browser", execute_browser)

    builder.set_entry_point("classify")
    builder.add_conditional_edges(
        "classify",
        route_by_type,
        {
            "execute_simple": "execute_simple",
            "execute_browser": "execute_browser",
        },
    )
    builder.add_edge("execute_simple", END)
    builder.add_edge("execute_browser", END)

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
    initial_state: AgentState = {
        "task_id": task_id,
        "user_id": user_id,
        "prompt": prompt,
        "task_type": "simple",
        "messages": [],
        "result": "",
        "tokens_used": 0,
        "credits_used": 0,
        "error": None,
        "metadata": {},
    }

    try:
        final_state = await pipeline.ainvoke(initial_state)
        return {
            "result": final_state.get("result", ""),
            "task_type": final_state.get("task_type", "simple"),
            "tokens_used": final_state.get("tokens_used", 0),
            "credits_used": final_state.get("credits_used", 1),
            "error": final_state.get("error"),
            "metadata": final_state.get("metadata", {}),
        }
    except Exception as exc:
        logger.exception("Pipeline failed for task %s", task_id)
        return {
            "result": "",
            "task_type": "simple",
            "tokens_used": 0,
            "credits_used": 1,
            "error": str(exc),
            "metadata": {},
        }
