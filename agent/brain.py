import asyncio
import logging
import os
import random
import re
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
    def registrar_lead_crm(
        nombre: str,
        empresa: str,
        interes: str,
        sector: str | None = None,
        actividad: str | None = None,
        empleados: str | None = None,
    ) -> dict:
        """Registra un lead comercial en el CRM, junto con el perfil de su empresa."""
        return tools.registrar_lead_crm(nombre, telefono, empresa, interes, sector, actividad, empleados)

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

    def reclasificar_caso_sin_licencia(caso_id: str, nombre: str) -> dict:
        """Si ya existía un radicado de soporte (caso_id tipo ESC-123) y luego
        consultar_licencia devuelve sin_licencia: comenta y bloquea ese caso en el CRM,
        y lo reescala a comercial."""
        return tools.reclasificar_caso_sin_licencia(caso_id, telefono, nombre)

    def registrar_cliente(
        numero_identificacion: str | None = None,
        nit_empresa: str | None = None,
        nombre_empresa: str | None = None,
        sector: str | None = None,
        actividad: str | None = None,
        empleados: str | None = None,
    ) -> dict:
        """Marca al remitente actual como cliente confirmado, guardando su identificación
        (y el perfil de su empresa, si aplica). Requiere que el contacto ya exista."""
        return tools.registrar_cliente(
            telefono, numero_identificacion, nit_empresa, nombre_empresa, sector, actividad, empleados
        )

    return [
        registrar_lead_crm,
        consultar_estado_cliente,
        guardar_datos_contacto,
        agendar_cita,
        crear_ticket_soporte,
        escalar_a_humano,
        reclasificar_caso_sin_licencia,
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


def _sanitizar_input(texto: str) -> str:
    # Remove SQL/script keywords
    texto = re.sub(r"(?i)(drop|delete|update|insert|select|script|eval|exec)", "", texto)
    texto = re.sub(r"<script[^>]*>.*?</script>", "", texto, flags=re.DOTALL)
    return texto.strip()


async def generar_respuesta(
    mensaje: str,
    telefono: str,
    historial: list[dict] | None = None,
    herramientas: list | None = None,
    timeout_segundos: float = 30.0,
) -> str:
    """Genera respuesta usando Gemini con timeout y fallback."""
    if historial is None:
        historial = []

    # Sanitize input
    texto_usuario = _sanitizar_input(mensaje)

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
            # Send message with timeout
            try:
                respuesta = await asyncio.wait_for(
                    asyncio.to_thread(chat.send_message, texto_usuario),
                    timeout=timeout_segundos
                )
                texto = respuesta.text
                break
            except asyncio.TimeoutError:
                logger.warning("Timeout en Gemini para %s después de %.1fs", telefono, timeout_segundos)
                return random.choice(RESPUESTAS_FALLBACK)

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


def clasificar_intencion(texto: str) -> dict:
    """Classify intent from user message."""
    texto_lower = texto.lower()

    # Simple keyword matching
    if any(w in texto_lower for w in ["hola", "saludos", "buenos días", "buenas noches"]):
        return {"intencion": "bienvenida", "confianza": 0.95}
    elif any(w in texto_lower for w in ["precio", "costo", "valor", "cuánto cuesta"]):
        return {"intencion": "consultar_precio", "confianza": 0.9}
    elif any(w in texto_lower for w in ["agendar", "agenda", "demo", "cita", "reunión"]):
        return {"intencion": "agendar_cita", "confianza": 0.85}
    elif any(w in texto_lower for w in ["licencia", "estado", "vigencia", "suscripción"]):
        return {"intencion": "consultar_licencia", "confianza": 0.8}
    elif any(w in texto_lower for w in ["escala", "soporte", "urgente", "problema", "error"]):
        return {"intencion": "escalar_a_humano", "confianza": 0.75}
    else:
        return {"intencion": "unknown", "confianza": 0.3}


def consultar_precio_modulo(nombre_modulo: str, moneda: str = "EUR", cantidad: int = 1) -> dict:
    """Query module price from database."""
    if cantidad <= 0:
        return {"error": "Cantidad debe ser mayor a 0"}

    # ponytail: stub that would query Postgres (mocked in tests)
    modulos = {
        "Pro": {"precio": 999, "moneda": "EUR"},
        "Enterprise": {"precio": 2999, "moneda": "EUR"},
        "Starter": {"precio": 299, "moneda": "EUR"},
    }

    if nombre_modulo not in modulos:
        return {"error": f"Módulo '{nombre_modulo}' no encontrado"}

    resultado = modulos[nombre_modulo].copy()
    resultado["cantidad"] = cantidad
    resultado["total"] = resultado["precio"] * cantidad
    return resultado


def reclasificar_caso_sin_licencia(telefono: str, descripcion_caso: str) -> dict:
    """Check if user has license, reclassify if not."""
    # ponytail: stub (would query Firebird in production)
    return {
        "puede_procesar": True,
        "redirigir_a": None,
    }


def buscar_en_conocimiento(query: str, top_k: int = 3) -> dict:
    """Search knowledge base (stub: RAG deferred to EP-004)."""
    return {
        "query": query,
        "resultados": [],
        "nota": "RAG backend not yet implemented (EP-004)",
    }


def guardrails_check(texto: str) -> dict:
    """Check for harmful or injection attempts."""
    bloqueado = False
    razon = ""

    # Simple checks for obvious injection attempts
    if any(pattern in texto.lower() for pattern in [
        "ignora", "instrucción", "drop table", "delete from", "system:", "prompt:", "<script"
    ]):
        bloqueado = True
        razon = "Intento de inyección detectado"

    return {
        "bloqueado": bloqueado,
        "razon": razon,
        "riesgo": "alto" if bloqueado else "bajo",
    }
