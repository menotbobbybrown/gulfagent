"""
Tool registry — central place to register LangGraph tools.
Phase 1: empty. Phase 2 adds browser_tool, whatsapp_tool, etc.
"""

from langchain_core.tools import BaseTool, tool
import asyncio


@tool
def careem_ride_estimate(query: str):
    """Get ride estimates from Careem for a given origin and destination."""
    # This is a placeholder for the tool interface
    return "Use the specialized Careem connector for this task."

@tool
def noon_product_search(query: str):
    """Search for products on Noon.com (UAE)."""
    return "Use the specialized Noon connector for this task."

@tool
def talabat_food_delivery(query: str, location: str = "Dubai"):
    """Find restaurants and food delivery options on Talabat."""
    return "Use the specialized Talabat connector for this task."

@tool
def dubai_now_government_services(query: str):
    """Check fines and government services via DubaiNow."""
    return "Use the specialized DubaiNow connector for this task."


@tool
def execute_code_tool(code: str, language: str = "python"):
    """Execute Python code in a secure E2B sandbox. Safe for running user-provided code."""
    return "Use the SandboxExecutor for this task."


# Populated in Phase 2+
REGISTERED_TOOLS: list[BaseTool] = [
    careem_ride_estimate,
    noon_product_search,
    talabat_food_delivery,
    dubai_now_government_services,
    execute_code_tool,
]



def get_tools() -> list[BaseTool]:
    return REGISTERED_TOOLS


def register_tool(tool: BaseTool) -> None:
    REGISTERED_TOOLS.append(tool)
