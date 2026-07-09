import hashlib
import hmac
import os
from typing import Any, Optional

import httpx

from .base import MensajeEntrante, ProveedorWhatsApp


class ProveedorMeta(ProveedorWhatsApp):
    def __init__(self):
        self.token = os.getenv("META_ACCESS_TOKEN")
        self.phone_id = os.getenv("META_PHONE_NUMBER_ID")
        self.verify_token = os.getenv("META_VERIFY_TOKEN")
        self.app_secret = os.getenv("META_APP_SECRET")
        self.api_url = f"https://graph.facebook.com/v20.0/{self.phone_id}/messages"

    def validar_firma(self, cuerpo: bytes, firma: Optional[str]) -> bool:
        if not firma or not firma.startswith("sha256="):
            return False
        esperada = hmac.new(self.app_secret.encode(), cuerpo, hashlib.sha256).hexdigest()
        return hmac.compare_digest(firma[len("sha256="):], esperada)

    def validar_webhook(self, params: dict) -> Optional[str]:
        if (
            params.get("hub.mode") == "subscribe"
            and params.get("hub.verify_token") == self.verify_token
        ):
            return params.get("hub.challenge")
        return None

    def parsear_webhook(self, payload: dict) -> Optional[MensajeEntrante]:
        try:
            entry = payload["entry"][0]["changes"][0]["value"]
            mensajes = entry.get("messages")
            if not mensajes:
                return None
            msg = mensajes[0]
            if msg.get("type") != "text":
                return None
            telefono = msg["from"]
            texto = msg["text"]["body"]
            nombre = entry.get("contacts", [{}])[0].get("profile", {}).get("name")
            return MensajeEntrante(telefono=telefono, texto=texto, nombre=nombre)
        except (KeyError, IndexError):
            return None

    async def enviar_mensaje(self, telefono: str, texto: str) -> Any:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        body = {
            "messaging_product": "whatsapp",
            "to": telefono,
            "type": "text",
            "text": {"body": texto},
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.api_url, headers=headers, json=body)
            if resp.status_code >= 400:
                print("META ERROR BODY:", resp.text)
            resp.raise_for_status()
            return resp.json()
