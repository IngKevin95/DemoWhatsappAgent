import asyncio
import logging
import os
import random
from datetime import datetime

import yaml
from google import genai
from google.genai import errors, types

from . import tools

logger = logging.getLogger(__name__)

# ponytail: estas tools reciben `telefono` como identificador del remitente real,
# no como dato que el modelo deba inventar/extraer del texto. functools.partial no
# basta (inspect.signature sigue mostrando el parámetro), así que se envuelven a
# mano sin `telefono` en la firma expuesta al LLM.
def _tools_con_telefono(telefono: str) -> list:
    def registrar_lead_crm(nombre: str, empresa: str, interes: str) -> dict:
        """Registra un lead comercial en el CRM."""
        return tools.registrar_lead_crm(nombre, telefono, empresa, interes)

    def consultar_estado_cliente() -> dict:
        """Consulta el estado del lead/cliente en el CRM para el remitente actual."""
        return tools.consultar_estado_cliente(telefono)

    def guardar_datos_contacto(
        nombre: str,
        empresa: str | None = None,
        correo: str | None = None,
        ciudad: str | None = None,
    ) -> dict:
        """Guarda/actualiza los datos básicos de quien escribe (nombre, empresa, correo, ciudad)."""
        return tools.guardar_datos_contacto(telefono, nombre, empresa, correo, ciudad)

    def agendar_cita(nombre: str, motivo: str, fecha: str, hora: str, area: str) -> dict:
        """Agenda una cita si el horario pedido está libre en el calendario de la primera
        persona disponible de esa área (según su rango horario propio). fecha: 'YYYY-MM-DD'.
        hora: 'HH:MM', debe ser una de HORARIOS_DISPONIBLES (09:00, 10:30, 14:00, 16:00)."""
        return tools.agendar_cita(nombre, telefono, motivo, fecha, hora, area)

    def crear_ticket_soporte(descripcion: str, modulo: str) -> dict:
        """Crea un ticket de soporte para el remitente actual."""
        return tools.crear_ticket_soporte(telefono, descripcion, modulo)

    def escalar_a_humano(nombre: str, resumen_caso: str, area: str) -> dict:
        """Escala la conversación a un agente humano del área dada."""
        return tools.escalar_a_humano(telefono, nombre, resumen_caso, area)

    def registrar_cliente(numero_identificacion: str | None = None, nit_empresa: str | None = None) -> dict:
        """Marca al remitente actual como cliente confirmado, guardando su identificación
        (y la de su empresa, si aplica). Requiere que el contacto ya exista."""
        return tools.registrar_cliente(telefono, numero_identificacion, nit_empresa)

    return [
        registrar_lead_crm,
        consultar_estado_cliente,
        guardar_datos_contacto,
        agendar_cita,
        crear_ticket_soporte,
        escalar_a_humano,
        registrar_cliente,
    ]

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

TOOL_FUNCTIONS_FIJAS = [
    tools.buscar_en_knowledge,
    tools.consultar_precio_modulo,
    tools.consultar_disponibilidad_agenda,
    tools.consultar_ticket_soporte,
    tools.consultar_licencia,
    tools.crear_tarea,
    tools.consultar_ofertas_activas,
    tools.consultar_parametro,
]


def _tools_para(telefono: str) -> list:
    return TOOL_FUNCTIONS_FIJAS + _tools_con_telefono(telefono)

MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3.1-flash-lite")


def _historial_a_contenido(historial: list[dict]) -> list[types.Content]:
    return [
        types.Content(
            role="model" if m["role"] == "assistant" else "user",
            parts=[types.Part(text=m["content"])],
        )
        for m in historial
    ]


def _retry_delay_segundos(exc: errors.ClientError, default: float = 5.0) -> float:
    # ponytail: parseo best-effort del retryDelay que manda la API ("31s"); si no viene, default fijo.
    try:
        for detail in exc.details.get("error", {}).get("details", []):
            if detail.get("@type", "").endswith("RetryInfo"):
                return float(detail.get("retryDelay", f"{default}s").rstrip("s"))
    except Exception:
        pass
    return default


async def generar_respuesta(telefono: str, texto_usuario: str, historial: list[dict]) -> str:
    texto = None
    for intento in range(2):
        try:
            chat = client.chats.create(
                model=MODEL_NAME,
                history=_historial_a_contenido(historial),
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT + f"\n\nFecha de hoy: {datetime.now().strftime('%Y-%m-%d')}.",
                    tools=_tools_para(telefono),
                ),
            )
            # ponytail: send_message es sync y ejecuta el function-calling automático
            # (incluye las tools de agent/tools.py, todas sync) dentro de su propia
            # llamada — a to_thread para no bloquear el event loop de Uvicorn.
            respuesta = await asyncio.to_thread(chat.send_message, texto_usuario)
            texto = respuesta.text
            break
        except errors.ClientError as e:
            if e.code == 429 and intento == 0:
                espera = _retry_delay_segundos(e)
                logger.warning("429 de Gemini para %s, reintentando en %.1fs", telefono, espera)
                await asyncio.sleep(espera)
                continue
            logger.exception("Fallo generando respuesta para %s", telefono)
            break
        except Exception:
            logger.exception("Fallo generando respuesta para %s", telefono)
            break

    return texto if texto else random.choice(RESPUESTAS_FALLBACK)
