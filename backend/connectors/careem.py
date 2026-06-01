import logging
import json
from typing import Any
from agents.browser_agent import BrowserAgent

logger = logging.getLogger(__name__)

class CareemConnector:
    """Connector for Careem ride estimates."""
    
    def __init__(self, task_id: str, user_id: str):
        self.task_id = task_id
        self.user_id = user_id

    async def run(self, query: str, context: dict[str, Any] = None) -> dict[str, Any]:
        """
        Use browser-use to get ride estimates from Careem.
        Since we don't have an API key, we use the browser agent.
        """
        agent = BrowserAgent(
            task_id=self.task_id,
            user_id=self.user_id,
            headless=True
        )
        
        prompt = (
            f"Go to careem.com and find ride estimates for the following query: {query}. "
            "Extract the ride types, prices, and ETAs. "
            "Return the data in structured JSON format with keys: options (list of {type, price, eta})."
        )
        
        try:
            result = await agent.run(prompt)
            if result.success:
                # Try to parse JSON from the result text
                try:
                    # Simple extraction logic - LLM should have returned JSON
                    text = result.result
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    if start != -1 and end != -1:
                        data = json.loads(text[start:end])
                        return {"data": data, "error": None, "metadata": result.steps}
                except:
                    pass
                return {"data": {"raw_result": result.result}, "error": None, "metadata": result.steps}
            else:
                return {"data": None, "error": result.error}
        finally:
            agent.cleanup()

def register():
    # Registration logic if needed
    pass
