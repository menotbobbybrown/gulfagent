import logging
import json
from typing import Any
from agents.browser_agent import BrowserAgent

logger = logging.getLogger(__name__)

class DubaiNowConnector:
    """Connector for DubaiNow government services."""
    
    def __init__(self, task_id: str, user_id: str):
        self.task_id = task_id
        self.user_id = user_id

    async def run(self, query: str, context: dict[str, Any] = None) -> dict[str, Any]:
        """
        Use browser-use to navigate Dubai government services.
        """
        agent = BrowserAgent(
            task_id=self.task_id,
            user_id=self.user_id,
            headless=True
        )
        
        prompt = (
            f"Navigate to dubaipay.gov.ae or relevant Dubai government portal to check: {query}. "
            "Extract information like fine balance, due dates, or renewal reminders. "
            "Return the data in structured JSON format."
        )
        
        try:
            result = await agent.run(prompt)
            if result.success:
                try:
                    text = result.result
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    if start != -1 and end != -1:
                        data = json.loads(text[start:end])
                        return {"data": data, "error": None}
                except:
                    pass
                return {"data": {"raw_result": result.result}, "error": None}
            else:
                return {"data": None, "error": result.error}
        finally:
            agent.cleanup()
