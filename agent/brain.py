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
from .middleware.circuit_breaker import CircuitBreaker
from .prometheus_metrics import demobot_errors_total

logger = logging.getLogger(__name__)

def _fallback_generar_respuesta(*args, **kwargs) -> str:
    """Fallback cuando circuit breaker abre (Gemini caído)."""
    return _get_fallback_message()

# FIX-REPAIR-004: Timeout config from .env
GEMINI_TIMEOUT_SECONDS = float(os.getenv('GEMINI_TIMEOUT_SECONDS', '10.0'))
GEMINI_YELLOW_ZONE_SECONDS = 5.0  # Warn if latency > this

_circuit_breaker_gemini = CircuitBreaker(
    name="Gemini",
    failure_threshold=int(os.getenv('CIRCUIT_BREAKER_THRESHOLD', '3')),
    recovery_timeout=int(os.getenv('CIRCUIT_BREAKER_WINDOW_SEC', '30')),
    fallback_fn=_fallback_generar_respuesta,
)

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

    def _registrar_cliente(numero_identificacion: str | None = None, nit_empresa: str | None = None, nombre_empresa: str | None = None, sector: str | None = None, actividad: str | None = None, empleados: str | None = None) -> dict:
        """Marca un contacto como cliente confirmado y guarda sus datos de identificación empresarial/personal."""
        return tools.registrar_cliente(
            telefono, numero_identificacion, nit_empresa, nombre_empresa, sector, actividad, empleados
        )

    def _finalizar_conversacion(motivo_cierre: str = "usuario") -> dict:
        """Cierra la conversación actual de forma explícita.
        Debe llamarse cuando el usuario se despide o indica que ya no requiere más ayuda."""
        return tools.finalizar_conversacion(telefono, motivo_cierre)

    return [
        registrar_lead_crm,
        consultar_estado_cliente,
        guardar_datos_contacto,
        agendar_cita,
        crear_ticket_soporte,
        escalar_a_humano,
        reclasificar_caso_sin_licencia,
        _registrar_cliente,
        _finalizar_conversacion,
    ]

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def _get_fallback_message() -> str:
    # Obtener el horario de atención desde la base de datos o usar default
    horario = "Lunes a Viernes de 8am a 6pm"
    try:
        from .db import SyncSession, Parametro
        with SyncSession() as session:
            param = session.query(Parametro).filter(Parametro.clave == "horario_atencion").first()
            if param and param.valor:
                horario = param.valor
    except Exception as e:
        logger.error(f"Error al obtener horario_atencion de la base de datos: {e}")
    
    return f"Servicio temporalmente inactivo, será contactado a la mayor brevedad en el horario de {horario}."


class FallbackDetector(list):
    def __contains__(self, item):
        if not isinstance(item, str):
            return False
        old_fallbacks = [
            "Disculpa, se me cruzaron los cables un segundo 😅 ¿me repites eso último?",
            "Uy, no logré procesar bien tu mensaje. ¿Puedes contarme de nuevo qué necesitas?",
            "Perdona la demora, tuve un pequeño inconveniente técnico. ¿En qué te ayudo?",
            "Se me fue el hilo por un momento, disculpa. ¿Me lo repites, por favor?",
        ]
        if item in old_fallbacks:
            return True
        if "Servicio temporalmente inactivo" in item:
            return True
        return False

RESPUESTAS_FALLBACK = FallbackDetector()

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")

with open(os.path.join(CONFIG_DIR, "prompts.yaml"), encoding="utf-8") as f:
    SYSTEM_PROMPT = yaml.safe_load(f)["system_prompt"]

TOOL_FUNCTIONS_FIJAS = [
    tools.buscar_en_knowledge,
    tools.consultar_precio_modulo,
    tools.consultar_combos,
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
    timeout_segundos: float = None,
) -> str:
    """FIX-REPAIR-004: Genera respuesta con timeout configurable y yellow zone logging."""
    # Use .env config if not specified
    if timeout_segundos is None:
        timeout_segundos = GEMINI_TIMEOUT_SECONDS
    if historial is None:
        historial = []

    # Sanitize input
    texto_usuario = _sanitizar_input(mensaje)

    texto = None
    tiempo_inicio = None
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
            # Send message with timeout + circuit breaker
            try:
                import time as time_module
                tiempo_inicio = time_module.time()

                # FIX-REPAIR-002: Apply circuit breaker to Gemini call.
                # CircuitBreaker.__call__ es un DECORADOR: envuelve la fn y
                # devuelve el wrapper; hay que EJECUTAR ese wrapper.
                def _send_with_cb():
                    wrapped = _circuit_breaker_gemini(
                        lambda: chat.send_message(texto_usuario)
                    )
                    return wrapped()

                respuesta = await asyncio.wait_for(
                    asyncio.to_thread(_send_with_cb),
                    timeout=timeout_segundos
                )
                # Check if result is fallback string (from circuit breaker)
                if isinstance(respuesta, str):
                    return respuesta
                texto = respuesta.text

                # FIX-REPAIR-004: Yellow zone logging if latency > 5s
                if tiempo_inicio:
                    latency = time_module.time() - tiempo_inicio
                    if latency > GEMINI_YELLOW_ZONE_SECONDS:
                        logger.warning(
                            f"Gemini latency YELLOW ZONE for {telefono}: {latency:.2f}s "
                            f"(threshold: {GEMINI_YELLOW_ZONE_SECONDS}s, timeout: {timeout_segundos}s)"
                        )
                break
            except asyncio.TimeoutError:
                demobot_errors_total.labels(error_type="gemini_timeout").inc()
                logger.warning("Timeout en Gemini para %s después de %.1fs", telefono, timeout_segundos)
                break

        except errors.ClientError as e:
            if e.code == 429 and intento == 0:
                demobot_errors_total.labels(error_type="gemini_rate_limit").inc()
                espera = _retry_delay_segundos(e)
                if espera <= 2.0:
                    logger.warning("429 de Gemini para %s, reintentando en %.1fs", telefono, espera)
                    await asyncio.sleep(espera)
                    continue
                else:
                    logger.warning("429 de Gemini para %s: espera de %.1fs excede límite seguro de webhook. No se reintenta.", telefono, espera)
            demobot_errors_total.labels(error_type="gemini_client_error").inc()
            logger.error("Error de cliente Gemini para %s (código %s): %s", telefono, getattr(e, 'code', 'N/A'), e)
            break
        except Exception as e:
            demobot_errors_total.labels(error_type="gemini_exception").inc()
            logger.error("Fallo inesperado generando respuesta para %s: %s", telefono, e)
            break

    if not texto:
        # Auto-escalar a humano en caso de caída del servicio/IA
        nombre = telefono
        try:
            from .db import SyncSession, Contacto
            with SyncSession() as session:
                contacto = session.get(Contacto, telefono)
                if contacto and contacto.nombre:
                    nombre = contacto.nombre
        except Exception as db_err:
            logger.error("No se pudo consultar el nombre del contacto en DB para auto-escalar: %s", db_err)

        try:
            from . import tools
            tools.escalar_a_humano(
                telefono=telefono,
                nombre=nombre,
                resumen_caso="Fallo en el servicio conversacional (Gemini API fuera de servicio, timeout o límite de cuota).",
                area="soporte"
            )
        except Exception as esc_err:
            logger.error("Fallo al auto-escalar conversación tras error de Gemini: %s", esc_err)

        texto = _get_fallback_message()

    return texto


async def clasificar_intencion(texto: str) -> str:
    """Classify intent from user message into 'comercial', 'soporte' or 'otro'."""
    try:
        response = await client.aio.models.generate_content(
            model=MODEL_NAME,
            contents=texto,
            config=types.GenerateContentConfig(
                system_instruction="Clasifica el siguiente mensaje en una sola palabra: 'comercial', 'soporte' u 'otro'. Responde únicamente con esa palabra.",
                temperature=0.0
            )
        )
        tipo = response.text.strip().lower()
        if tipo not in ["comercial", "soporte", "otro"]:
            return "otro"
        return tipo
    except Exception as e:
        logger.error("Fallo clasificando intencion: %s", e)
        return "otro"


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
    resultado["periodo"] = "anual"
    resultado["soporte"] = "incluye soporte técnico por un año"
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
