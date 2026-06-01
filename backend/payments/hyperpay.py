import logging
import httpx
from typing import Any
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class HyperPayClient:
    """
    HyperPay Server-to-Server API Client.
    Documentation: https://hyperpay.docs.oppwa.com/
    """
    
    def __init__(self):
        self.base_url = settings.hyperpay_base_url.rstrip("/")
        self.entity_id = settings.hyperpay_entity_id
        self.access_token = settings.hyperpay_access_token

    async def create_checkout_session(self, amount: float, currency: str = "AED", payment_type: str = "DB") -> dict[str, Any]:
        """
        Step 1: Request a checkout ID.
        """
        url = f"{self.base_url}/v1/checkouts"
        
        data = {
            "entityId": self.entity_id,
            "amount": f"{amount:.2f}",
            "currency": currency,
            "paymentType": payment_type,
        }
        
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, data=data, headers=headers)
                resp.raise_for_status()
                return {"data": resp.json(), "error": None}
        except Exception as e:
            logger.error("HyperPay checkout session failed: %s", e)
            return {"data": None, "error": str(e)}

    async def get_payment_status(self, checkout_id: str) -> dict[str, Any]:
        """
        Step 2: Get payment status after redirection.
        """
        url = f"{self.base_url}/v1/checkouts/{checkout_id}/payment"
        params = {
            "entityId": self.entity_id
        }
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params, headers=headers)
                resp.raise_for_status()
                return {"data": resp.json(), "error": None}
        except Exception as e:
            logger.error("HyperPay status check failed: %s", e)
            return {"data": None, "error": str(e)}

# API Router could go here or in a separate file
