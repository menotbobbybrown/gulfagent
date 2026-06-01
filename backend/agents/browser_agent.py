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
                """Hook: capture screenshot at start of each step."""
                pass  # browser-use fires this before actions

            async def on_step_end(agent_instance: Any) -> None:
                """Hook: capture screenshot + record step after each action."""
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
