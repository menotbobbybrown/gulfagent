"""
T33 — Evolution API setup and webhook registration
T36 — Send result back to user via WhatsApp
T37 — Approval messages: "Reply Y to approve, N to deny"

Evolution API docs: https://doc.evolution-api.com/v2
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Approval action labels for user-facing WhatsApp messages
ACTION_LABELS = {
    "email": "send an email",
    "form_submit": "submit a form",
    "payment": "make a payment",
    "file_delete": "delete a file",
}


class WhatsAppAgent:
    """Thin wrapper around Evolution API v2."""

    def __init__(self) -> None:
        self.base = settings.evolution_api_url.rstrip("/")
        self.api_key = settings.evolution_api_key
        self.instance = settings.whatsapp_instance

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

    async def send_text(self, phone: str, text: str) -> dict[str, Any]:
        """
        Send a plain-text WhatsApp message.
        phone: E.164 format without '+', e.g. "971501234567"
        """
        url = f"{self.base}/message/sendText/{self.instance}"
        payload = {
            "number": phone,
            "text": text,
            "options": {"delay": 500, "presence": "composing"},
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(url, json=payload, headers=self._headers())
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error("WhatsApp send_text failed to %s: %s", phone, e)
            return {"error": str(e)}

    async def send_result(self, phone: str, task_prompt: str, result: str) -> None:
        """Format and send a task result via WhatsApp."""
        # Truncate long results for WhatsApp
        MAX_CHARS = 3800
        if len(result) > MAX_CHARS:
            result = result[:MAX_CHARS] + "\n\n…[truncated — view full result on dashboard]"

        message = f"✅ *Task Complete*\n\n_{task_prompt[:150]}_\n\n{result}"
        await self.send_text(phone, message)

    async def send_error(self, phone: str, task_prompt: str, error: str) -> None:
        """Notify user of task failure."""
        message = (
            f"❌ *Task Failed*\n\n_{task_prompt[:150]}_\n\n"
            f"Error: {error[:500]}\n\nPlease try again or visit your dashboard."
        )
        await self.send_text(phone, message)

    async def send_approval_request(
        self,
        phone: str,
        action_type: str,
        payload_summary: str,
        approval_id: str,
    ) -> None:
        """
        T37 — Send approval prompt to user.
        User replies Y to approve, N to deny.
        """
        action_label = ACTION_LABELS.get(action_type, action_type)
        message = (
            f"⚠️ *Approval Required*\n\n"
            f"GulfAgent wants to *{action_label}*:\n\n"
            f"{payload_summary[:400]}\n\n"
            f"Reply *Y* to approve or *N* to deny.\n"
            f"_(Auto-denies in 5 minutes)_\n\n"
            f"Ref: `{approval_id[:8]}`"
        )
        await self.send_text(phone, message)

    async def register_webhook(self, webhook_url: str) -> dict[str, Any]:
        """
        T33 — Register webhook with Evolution API instance.
        Call this once during setup / deploy.
        """
        url = f"{self.base}/webhook/set/{self.instance}"
        payload = {
            "url": webhook_url,
            "webhook_by_events": True,
            "webhook_base64": False,
            "events": [
                "MESSAGES_UPSERT",
                "CONNECTION_UPDATE",
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(url, json=payload, headers=self._headers())
                resp.raise_for_status()
                result = resp.json()
                logger.info("Webhook registered: %s", webhook_url)
                return result
        except Exception as e:
            logger.error("Webhook registration failed: %s", e)
            return {"error": str(e)}

    async def get_instance_status(self) -> dict[str, Any]:
        """Check if the Evolution API instance is connected."""
        url = f"{self.base}/instance/connectionState/{self.instance}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self._headers())
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error("Instance status check failed: %s", e)
            return {"error": str(e)}


# Module-level singleton
whatsapp = WhatsAppAgent()
