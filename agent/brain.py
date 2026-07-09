import logging
import os
import random
from datetime import datetime

import yaml
from google import genai
from google.genai import types

from . import tools

logger = logging.getLogger(__name__)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ponytail: variedad fija para no sonar a bot roto si el LLM falla o calla.
# Escalar a variantes por idioma/tono si el negocio lo pide más adelante.
RESPUESTAS_FALLBACK = [
    "Disculpa, se me cruzaron los cables un segundo 😅 ¿me repites eso último?",
    "Uy, no logré procesar bien tu mensaje. ¿Puedes contarme de nuevo qué necesitas?",
    "Perdona la demora, tuve un pequeño inconveniente técnico. ¿En qué te ayudo?",
    "Se me fue el hilo por un momento, disculpa. ¿Me lo repites, por favor?",
]

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")

with open(os.path.join(CONFIG_DIR, "prompts.yaml"), encoding="utf-8") as f:
    SYSTEM_PROMPT = yaml.safe_load(f)["system_prompt"]

TOOL_FUNCTIONS = [
    tools.buscar_en_knowledge,
    tools.consultar_precio_modulo,
    tools.registrar_lead_crm,
    tools.consultar_estado_cliente,
    tools.agendar_cita,
    tools.consultar_disponibilidad_agenda,
    tools.crear_ticket_soporte,
    tools.consultar_ticket_soporte,
    tools.escalar_a_humano,
    tools.consultar_ofertas_activas,
    tools.consultar_parametro,
    tools.guardar_datos_contacto,
    tools.registrar_cliente,
]

MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3.1-flash-lite")


def _historial_a_contenido(historial: list[dict]) -> list[types.Content]:
    return [
        types.Content(
            role="model" if m["role"] == "assistant" else "user",
            parts=[types.Part(text=m["content"])],
        )
        for m in historial
    ]


async def generar_respuesta(telefono: str, texto_usuario: str, historial: list[dict]) -> str:
    try:
        chat = client.chats.create(
            model=MODEL_NAME,
            history=_historial_a_contenido(historial),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT + f"\n\nFecha de hoy: {datetime.now().strftime('%Y-%m-%d')}.",
                tools=TOOL_FUNCTIONS,
            ),
        )
        respuesta = chat.send_message(texto_usuario)
        texto = respuesta.text
    except Exception:
        logger.exception("Fallo generando respuesta para %s", telefono)
        texto = None

    return texto if texto else random.choice(RESPUESTAS_FALLBACK)
