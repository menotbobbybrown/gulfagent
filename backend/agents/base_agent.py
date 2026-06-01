"""
Shared abstract base class for all GulfAgent agents.

Defines a common interface:
- run(prompt) → result
- cleanup()
- status_check() → bool
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """
    Abstract base for all GulfAgent agent types.

    Each agent handles one task execution. Do not reuse instances across tasks.
    """

    def __init__(self, task_id: str, user_id: str) -> None:
        self.task_id = task_id
        self.user_id = user_id

    @abstractmethod
    async def run(self, prompt: str) -> Any:
        """Execute the agent task. Returns an agent-specific result object."""
        ...

    def cleanup(self) -> None:
        """Release any resources held by the agent. No-op by default."""
        pass

    def status_check(self) -> bool:
        """Return True if the agent's dependencies/connections are healthy."""
        return True