import logging
import httpx
from typing import Any
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class TabbyClient:
    """
    Tabby API Client for BNPL.
    Documentation: https://docs.tabby.ai/
    """
    
    def __init__(self):
        self.base_url = settings.tabby_base_url.rstrip("/")
        self.api_key = settings.tabby_api_key

    async def create_session(self, amount: float, user_email: str, items: list = None) -> dict[str, Any]:
        """Create a Tabby checkout session."""
        url = f"{self.base_url}/api/v2/checkout"
        
        payload = {
            "payment": {
                "amount": f"{amount:.2f}",
                "currency": "AED",
                "description": "GulfAgent Subscription Upgrade",
                "buyer": {
                    "email": user_email,
                },
                "order": {
                    "items": items or [{"name": "Subscription Plan", "quantity": 1, "unit_price": f"{amount:.2f}"}]
                }
            },
            "lang": "ar",
            "merchant_code": "gulfagent",
            "merchant_urls": {
                "success": f"{settings.next_public_app_url}/dashboard/billing/success",
                "cancel": f"{settings.next_public_app_url}/dashboard/billing/cancel",
                "failure": f"{settings.next_public_app_url}/dashboard/billing/failure",
            }
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                return {"data": resp.json(), "error": None}
        except Exception as e:
            logger.error("Tabby checkout failed: %s", e)
            return {"data": None, "error": str(e)}

class TamaraClient:
    """
    Tamara API Client for BNPL.
    Documentation: https://docs.tamara.co/
    """
    
    def __init__(self):
        self.base_url = settings.tamara_base_url.rstrip("/")
        self.api_key = settings.tamara_api_key

    async def create_checkout(self, amount: float, user_email: str) -> dict[str, Any]:
        """Create a Tamara checkout session."""
        url = f"{self.base_url}/checkout"
        
        payload = {
            "order_reference_id": "GA-" + user_email.split('@')[0],
            "total_amount": {"amount": amount, "currency": "AED"},
            "description": "GulfAgent Subscription",
            "country_code": "AE",
            "payment_type": "PAY_BY_INSTALMENTS",
            "consumer": {
                "email": user_email,
                "first_name": "Gulf",
                "last_name": "User"
            },
            "merchant_url": {
                "success": f"{settings.next_public_app_url}/dashboard/billing/success",
                "failure": f"{settings.next_public_app_url}/dashboard/billing/failure",
                "cancel": f"{settings.next_public_app_url}/dashboard/billing/cancel",
                "notification": f"{settings.next_public_app_url}/api/billing/tamara/webhook"
            }
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                return {"data": resp.json(), "error": None}
        except Exception as e:
            logger.error("Tamara checkout failed: %s", e)
            return {"data": None, "error": str(e)}
