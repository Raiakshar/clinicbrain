from abc import ABC, abstractmethod

import httpx

from app.config import settings


class WhatsAppError(Exception):
    pass


class BaseWhatsAppProvider(ABC):
    @abstractmethod
    async def send(self, to_phone: str, message: str) -> None:
        """Raise WhatsAppError on failure."""


class SimulatedProvider(BaseWhatsAppProvider):
    async def send(self, to_phone: str, message: str) -> None:
        if to_phone.startswith("000"):
            raise WhatsAppError(f"simulated failure for {to_phone}")


class MetaCloudProvider(BaseWhatsAppProvider):
    async def send(self, to_phone: str, message: str) -> None:
        url = f"https://graph.facebook.com/v19.0/{settings.meta_phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "text",
            "text": {"body": message},
        }
        headers = {
            "Authorization": f"Bearer {settings.meta_access_token}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
        except Exception as e:
            raise WhatsAppError(str(e)) from e


def get_whatsapp_provider() -> BaseWhatsAppProvider:
    if settings.whatsapp_provider == "meta":
        return MetaCloudProvider()
    return SimulatedProvider()
