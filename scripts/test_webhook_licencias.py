"""Simula 3 conversaciones de WhatsApp (via webhook local) para las identificaciones
sembradas en Firebird, con delay entre turnos para no golpear el rate limit de Gemini.
No requiere WhatsApp real: firma el payload con META_APP_SECRET como lo haría Meta."""
import hashlib
import hmac
import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

URL = "http://localhost:8000/webhook"
APP_SECRET = os.environ["META_APP_SECRET"]
PHONE_NUMBER_ID = os.environ["META_PHONE_NUMBER_ID"]
DELAY_SEGUNDOS = 20

CASOS = [
    ("573001110001", "900111222", "con_licencia_con_soporte"),
    ("573002220002", "900333444", "con_licencia_sin_soporte"),
    ("573003330003", "900555666", "sin_licencia"),
]


def _payload(wa_id: str, texto: str) -> dict:
    return {
        "entry": [{
            "changes": [{
                "value": {
                    "metadata": {"phone_number_id": PHONE_NUMBER_ID},
                    "messages": [{"from": wa_id, "type": "text", "text": {"body": texto}}],
                }
            }]
        }]
    }


def _firmar(cuerpo: bytes) -> str:
    return "sha256=" + hmac.new(APP_SECRET.encode(), cuerpo, hashlib.sha256).hexdigest()


def enviar(wa_id: str, texto: str):
    cuerpo = httpx.Request("POST", URL, json=_payload(wa_id, texto)).content
    firma = _firmar(cuerpo)
    r = httpx.post(URL, content=cuerpo, headers={
        "Content-Type": "application/json",
        "X-Hub-Signature-256": firma,
    }, timeout=30)
    print(f"  -> [{wa_id}] {texto!r} => {r.status_code} {r.text[:200]}")
    return r


def demo():
    for wa_id, identificacion, escenario in CASOS:
        print(f"\n=== {escenario} ({identificacion}) ===")
        enviar(wa_id, "Hola, soy Carlos Pérez, necesito soporte con el sistema")
        time.sleep(DELAY_SEGUNDOS)
        enviar(wa_id, f"Mi cédula es {identificacion}, tengo un problema con el módulo de Facturación")
        time.sleep(DELAY_SEGUNDOS)
    print("\nListo. Revisa logs de demobot (docker compose logs -f demobot) para ver las respuestas.")


if __name__ == "__main__":
    demo()
