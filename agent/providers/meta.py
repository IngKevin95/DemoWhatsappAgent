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
            
            telefono = msg["from"]
            nombre = entry.get("contacts", [{}])[0].get("profile", {}).get("name")
            
            if msg.get("type") == "text":
                texto = msg["text"]["body"]
                return MensajeEntrante(telefono=telefono, texto=texto, nombre=nombre, mensaje_id=msg.get("id"))
            elif msg.get("type") == "interactive" and msg.get("interactive", {}).get("type") == "button_reply":
                texto = msg["interactive"]["button_reply"]["id"]
                return MensajeEntrante(telefono=telefono, texto=texto, nombre=nombre, mensaje_id=msg.get("id"))
            elif msg.get("type") == "audio":
                media_id = msg["audio"]["id"]
                return MensajeEntrante(telefono=telefono, texto="", nombre=nombre, tipo="audio", media_id=media_id, mensaje_id=msg.get("id"))
            elif msg.get("type") == "document":
                media_id = msg["document"]["id"]
                return MensajeEntrante(telefono=telefono, texto="", nombre=nombre, tipo="document", media_id=media_id, mensaje_id=msg.get("id"))
            else:
                return None
                
        except (KeyError, IndexError):
            return None

    async def enviar_mensaje(
        self, 
        telefono: str, 
        texto: str, 
        botones: Optional[list[dict]] = None,
        template: Optional[dict] = None,
        documento: Optional[dict] = None
    ) -> Any:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        
        if template:
            body = {
                "messaging_product": "whatsapp",
                "to": telefono,
                "type": "template",
                "template": template
            }
        elif documento:
            body = {
                "messaging_product": "whatsapp",
                "to": telefono,
                "type": "document",
                "document": documento
            }
        elif botones:
            if len(botones) > 3:
                raise ValueError("Meta API only supports up to 3 buttons")
            
            meta_buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": b["id"],
                        "title": b["title"]
                    }
                } for b in botones
            ]
            
            body = {
                "messaging_product": "whatsapp",
                "to": telefono,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {
                        "text": texto
                    },
                    "action": {
                        "buttons": meta_buttons
                    }
                }
            }
        else:
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

    async def descargar_media(self, media_id: str) -> bytes:
        headers = {
            "Authorization": f"Bearer {self.token}",
        }
        # First get the media URL
        media_info_url = f"https://graph.facebook.com/v20.0/{media_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(media_info_url, headers=headers)
            resp.raise_for_status()
            media_url = resp.json()["url"]
            
            # Then download the actual bytes
            resp_media = await client.get(media_url, headers=headers)
            resp_media.raise_for_status()
            return resp_media.content
