"""
T21 — Install browser-use, wrap in BrowserAgent class
T22 — run(prompt) → returns result + screenshots

browser-use: https://github.com/browser-use/browser-use
Requires: pip install browser-use && playwright install chromium
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BrowserStep:
    """One action the agent took during browsing."""
    step_number: int
    action: str          # e.g. "navigate", "click", "type", "extract"
    description: str
    url: str | None = None
    screenshot_path: str | None = None  # local tmp path before upload
    screenshot_url: str | None = None   # Supabase Storage URL after upload


@dataclass
class BrowserResult:
    """Outcome of a browser agent run."""
    success: bool
    result: str
    steps: list[BrowserStep] = field(default_factory=list)
    error: str | None = None
    tokens_used: int = 0
    credits_used: int = 0


class BrowserAgent:
    """
    Wraps browser-use Agent for GulfAgent task execution.

    Each instance handles one task run. Do not reuse across tasks.
    Screenshots are saved to a temp dir and returned for upload to
    Supabase Storage (T23).
    """

    # Destructive action patterns — triggers approval flow
    DESTRUCTIVE_ACTIONS = {
        "submit_form": "form_submit",
        "send_email": "email",
        "click_payment": "payment",
        "delete_file": "file_delete",
        "confirm_order": "payment",
        "checkout": "payment",
    }

    def __init__(
        self,
        task_id: str,
        user_id: str,
        headless: bool = True,
        timeout_seconds: int = 300,
    ) -> None:
        self.task_id = task_id
        self.user_id = user_id
        self.headless = headless
        self.timeout_seconds = timeout_seconds
        self._steps: list[BrowserStep] = []
        self._screenshot_dir = Path(tempfile.mkdtemp(prefix=f"ga_browser_{task_id[:8]}_"))

    async def _check_destructive_action(self, action_str: str, agent_instance: Any = None) -> None:
        """
        Check if the action matches a destructive pattern.
        If so, trigger the approval flow and raise ApprovalRequiredError.

        Called from on_step_end and on_step_start hooks.
        Must be async since it calls the DB and approval manager.
        """
        action_lower = action_str.lower()

        matched_type: str | None = None
        for pattern, action_type in self.DESTRUCTIVE_ACTIONS.items():
            if pattern in action_lower:
                matched_type = action_type
                break

        if not matched_type:
            return

        # Build a safe summary of what the agent is about to do
        payload = {
            "action": action_lower[:500],
            "matched_pattern": matched_type,
            "task_id": self.task_id,
            "step_count": len(self._steps) + 1,
        }

        # Record the destructive action in the task metadata and trigger approval
        from core.approval_manager import request_approval
        from db.session import AsyncSessionLocal
        from sqlalchemy import update
        from db.models import Task
        from uuid import UUID

        async with AsyncSessionLocal() as session:
            # Append destructive_action info to existing metadata (don't overwrite)
            from sqlalchemy import select
            existing = await session.execute(
                select(Task.metadata).where(Task.id == UUID(self.task_id))
            )
            current_meta = existing.scalar_one_or_none() or {}

            updated_meta = dict(current_meta) if isinstance(current_meta, dict) else {}
            updated_meta["destructive_action"] = {
                "pattern": matched_type,
                "action": action_lower[:500],
            }

            await session.execute(
                update(Task)
                .where(Task.id == UUID(self.task_id))
                .values(metadata=updated_meta)
            )
            await session.commit()

            logger.warning(
                "Destructive action detected: pattern=%s action=%s task=%s",
                matched_type, action_lower[:100], self.task_id,
            )

            # This will raise ApprovalRequiredError (blocks until decided)
            await request_approval(
                session=session,
                task_id=self.task_id,
                action_type=matched_type,
                payload=payload,
            )

    async def run(self, prompt: str) -> BrowserResult:
        """
        Execute a browser task.
        Returns BrowserResult with steps + screenshots.
        Raises ApprovalRequiredError before destructive actions.
        """
        try:
            from browser_use import Agent, Browser, BrowserConfig
            from langchain_anthropic import ChatAnthropic

            from config import get_settings
            settings = get_settings()

            llm = ChatAnthropic(
                model="claude-sonnet-4-20250514",
                api_key=settings.anthropic_api_key,
                temperature=0,
            )

            browser_config = BrowserConfig(
                headless=self.headless,
                disable_security=False,
            )
            browser = Browser(config=browser_config)

            step_counter = {"n": 0}

            async def on_step_start(agent_instance: Any) -> None:
                """Hook: before each step — check for destructive planned actions."""
                # Check if the next planned action contains destructive patterns
                try:
                    if hasattr(agent_instance, "state") and hasattr(agent_instance.state, "next_plan"):
                        next_plan = agent_instance.state.next_plan
                        if next_plan:
                            plan_str = str(next_plan).lower()
                            await self._check_destructive_action(plan_str, agent_instance)
                except ApprovalRequiredError:
                    raise
                except Exception as e:
                    logger.debug("on_step_start check error: %s", e)

            async def on_step_end(agent_instance: Any) -> None:
                """Hook: capture screenshot + record step + check for destructive actions."""
                step_counter["n"] += 1
                n = step_counter["n"]

                try:
                    # Get current page state from browser-use agent
                    history = agent_instance.state.history
                    last_action = ""
                    last_url = None

                    if history and history.history:
                        last_entry = history.history[-1]
                        if last_entry.model_actions:
                            last_action = str(last_entry.model_actions[0])
                        if last_entry.state and last_entry.state.url:
                            last_url = last_entry.state.url

                    # Check if the action just executed is destructive
                    await self._check_destructive_action(last_action, agent_instance)

                    screenshot_path = None
                    try:
                        page = await browser.get_current_page()
                        if page:
                            screenshot_bytes = await page.screenshot(full_page=False)
                            screenshot_path = str(self._screenshot_dir / f"step_{n:03d}.png")
                            Path(screenshot_path).write_bytes(screenshot_bytes)
                    except Exception as ss_err:
                        logger.debug("Screenshot failed at step %d: %s", n, ss_err)

                    self._steps.append(BrowserStep(
                        step_number=n,
                        action=last_action[:200] if last_action else "action",
                        description=f"Step {n}",
                        url=last_url,
                        screenshot_path=screenshot_path,
                    ))
                except ApprovalRequiredError:
                    raise
                except Exception as step_err:
                    logger.debug("Step hook error at %d: %s", n, step_err)

            # Create and run the agent
            agent = Agent(
                task=prompt,
                llm=llm,
                browser=browser,
                use_vision=True,
            )

            # Register hooks if available (browser-use >=0.2.0)
            if hasattr(agent, "register_hooks"):
                agent.register_hooks(on_step_end=on_step_end)

            result = await asyncio.wait_for(
                agent.run(max_steps=25),
                timeout=self.timeout_seconds,
            )

            await browser.close()

            # Extract result text
            result_text = ""
            if hasattr(result, "final_result"):
                result_text = result.final_result() or ""
            elif hasattr(result, "__str__"):
                result_text = str(result)

            # Estimate credits: base 50 + 2 per step
            credits = 50 + (len(self._steps) * 2)

            return BrowserResult(
                success=True,
                result=result_text,
                steps=self._steps,
                credits_used=credits,
            )

        except asyncio.TimeoutError:
            logger.error("Browser agent timed out for task %s", self.task_id)
            return BrowserResult(
                success=False,
                result="",
                steps=self._steps,
                error="Browser agent timed out after 5 minutes.",
                credits_used=10,
            )
        except ImportError as e:
            logger.error("browser-use not installed: %s", e)
            return BrowserResult(
                success=False,
                result="",
                error="browser-use not installed. Run: pip install browser-use && playwright install chromium",
            )
        except Exception as e:
            logger.exception("Browser agent error for task %s", self.task_id)
            return BrowserResult(
                success=False,
                result="",
                steps=self._steps,
                error=str(e),
                credits_used=10,
            )

    def cleanup(self) -> None:
        """Remove temp screenshot directory."""
        import shutil
        try:
            shutil.rmtree(self._screenshot_dir, ignore_errors=True)
        except Exception:
            pass
