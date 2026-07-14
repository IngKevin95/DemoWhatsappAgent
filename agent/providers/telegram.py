import os
from typing import Any, Optional
import httpx

from .base import MensajeEntrante, ProveedorWhatsApp

class ProveedorTelegram(ProveedorWhatsApp):
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
        self.api_url = f"https://api.telegram.org/bot{self.token}"

    def validar_webhook(self, params: dict) -> Optional[str]:
        # Telegram sets webhooks via an API call and doesn't do a GET challenge like Meta.
        # We just return a static string to signify success if called.
        return "ok"

    def validar_firma(self, cuerpo: bytes, firma: Optional[str]) -> bool:
        # Telegram sends the secret token in X-Telegram-Bot-Api-Secret-Token header
        if not self.webhook_secret:
            return True # If not configured, we assume valid
        return firma == self.webhook_secret

    def parsear_webhook(self, payload: dict) -> Optional[MensajeEntrante]:
        try:
            if "message" not in payload:
                return None
                
            msg = payload["message"]
            telefono = str(msg["chat"]["id"]) # Telegram uses chat_id instead of phone number
            nombre = msg.get("from", {}).get("first_name")
            
            if "text" in msg:
                texto = msg["text"]
                return MensajeEntrante(telefono=telefono, texto=texto, nombre=nombre)
            
            # Additional logic for audio/documents could go here later
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
        # Basic implementation mapping to Telegram sendMessage
        
        body = {
            "chat_id": telefono,
            "text": texto,
        }
        
        # We can implement inline keyboards for `botones`
        if botones:
            inline_keyboard = [[{"text": b["title"], "callback_data": b["id"]}] for b in botones]
            body["reply_markup"] = {"inline_keyboard": inline_keyboard}

        # Template and document to be implemented fully if needed, for now we just handle text/buttons.
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.api_url}/sendMessage", json=body)
            if resp.status_code >= 400:
                print("TELEGRAM ERROR BODY:", resp.text)
            resp.raise_for_status()
            return resp.json()
