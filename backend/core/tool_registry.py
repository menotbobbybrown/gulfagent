"""
Tool registry — central place to register LangGraph tools.
Phase 1: empty. Phase 2 adds browser_tool, whatsapp_tool, etc.
"""

from langchain_core.tools import BaseTool

# Populated in Phase 2+
REGISTERED_TOOLS: list[BaseTool] = []


def get_tools() -> list[BaseTool]:
    return REGISTERED_TOOLS


def register_tool(tool: BaseTool) -> None:
    REGISTERED_TOOLS.append(tool)
