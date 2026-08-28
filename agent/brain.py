import asyncio
import logging
import os
import random
import re
from datetime import datetime

import yaml
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from . import tools
from .middleware.circuit_breaker import CircuitBreaker
from .prometheus_metrics import demobot_errors_total

logger = logging.getLogger(__name__)

def _fallback_generar_respuesta(*args, **kwargs) -> str:
    """Fallback cuando circuit breaker abre (Gemini cado)."""
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
        """Guarda/actualiza los datos bsicos de quien escribe (nombre, empresa, correo, ciudad)."""
        return tools.guardar_datos_contacto(telefono, nombre, empresa, correo, ciudad)

    def agendar_cita(nombre: str, motivo: str, fecha: str, hora: str, area: str) -> dict:
        """Agenda una cita si el horario pedido est libre en el calendario de la primera
        persona disponible de esa rea (segn su rango horario propio). fecha: 'YYYY-MM-DD'.
        hora: 'HH:MM', debe ser una de HORARIOS_DISPONIBLES (09:00, 10:30, 14:00, 16:00)."""
        return tools.agendar_cita(nombre, telefono, motivo, fecha, hora, area)

    def crear_ticket_soporte(descripcion: str, modulo: str) -> dict:
        """Crea un ticket de soporte para el remitente actual.
        Regla importante: Crea el ticket y documenta en la descripcin ('descripcion') el problema reportado.
        DEBES informarle al usuario el nmero de radicado (ticket_id) y TAMBIN el nmero de caso del CRM (crm_case_number), si este ltimo est disponible.
        Luego, intenta brindar ayuda tcnica directamente al usuario.
        Solo si tu ayuda no es suficiente o el usuario pide ms ayuda, llama a escalar_a_humano."""
        return tools.crear_ticket_soporte(telefono, descripcion, modulo)

    def escalar_a_humano(nombre: str, resumen_caso: str, area: str) -> dict:
        """Escala la conversacin a un agente humano del rea dada."""
        return tools.escalar_a_humano(telefono, nombre, resumen_caso, area)

    def reclasificar_caso_sin_licencia(caso_id: str, nombre: str) -> dict:
        """Si ya exista un radicado de soporte (caso_id tipo ESC-123) y luego
        consultar_licencia devuelve sin_licencia: comenta y bloquea ese caso en el CRM,
        y lo reescala a comercial."""
        return tools.reclasificar_caso_sin_licencia(caso_id, telefono, nombre)

    def _registrar_cliente(numero_identificacion: str | None = None, nit_empresa: str | None = None, nombre_empresa: str | None = None, sector: str | None = None, actividad: str | None = None, empleados: str | None = None) -> dict:
        """Marca un contacto como cliente confirmado y guarda sus datos de identificacin empresarial/personal."""
        return tools.registrar_cliente(
            telefono, numero_identificacion, nit_empresa, nombre_empresa, sector, actividad, empleados
        )

    def _finalizar_conversacion(motivo_cierre: str = "usuario") -> dict:
        """Cierra la conversacin actual de forma explcita.
        Debe llamarse cuando el usuario se despide o indica que ya no requiere ms ayuda."""
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


def _get_fallback_message() -> str:
    horario = "Lunes a Viernes de 8am a 6pm"
    try:
        from .db import SyncSession, Parametro
        with SyncSession() as session:
            param = session.query(Parametro).filter(Parametro.clave == "horario_atencion").first()
            if param and param.valor:
                horario = param.valor
    except Exception as e:
        logger.error(f"Error al obtener horario_atencion de la base de datos: {e}")
    
    return f"Servicio temporalmente inactivo, ser contactado a la mayor brevedad en el horario de {horario}."


class FallbackDetector(list):
    def __contains__(self, item):
        if not isinstance(item, str):
            return False
        old_fallbacks = [
            "Disculpa, se me cruzaron los cables un segundo Y~. me repites eso ltimo?",
            "Uy, no logr procesar bien tu mensaje. Puedes contarme de nuevo qu necesitas?",
            "Perdona la demora, tuve un pequeo inconveniente tcnico. En qu te ayudo?",
            "Se me fue el hilo por un momento, disculpa. Me lo repites, por favor?",
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

def _get_lc_tools(telefono: str) -> list:
    lc_tools = []
    for fn in TOOL_FUNCTIONS_FIJAS:
        lc_tools.append(StructuredTool.from_function(fn))
    for fn in _tools_con_telefono(telefono):
        lc_tools.append(StructuredTool.from_function(fn))
    return lc_tools


MODEL_NAME = os.getenv("MODEL_NAME", "gemini-1.5-flash") # Updated to supported LangChain model

# Initialize the LangChain Chat model
llm = ChatGoogleGenerativeAI(
    model=MODEL_NAME,
    api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.0
)

def _historial_a_lc_messages(historial: list[dict], sys_inst: str) -> list:
    messages = [SystemMessage(content=sys_inst)]
    for m in historial:
        if m["role"] == "assistant":
            messages.append(AIMessage(content=m["content"]))
        else:
            messages.append(HumanMessage(content=m["content"]))
    return messages


def _sanitizar_input(texto: str) -> str:
    texto = re.sub(r"(?i)(drop|delete|update|insert|select|script|eval|exec)", "", texto)
    texto = re.sub(r"<script[^>]*>.*?</script>", "", texto, flags=re.DOTALL)
    return texto.strip()


async def generar_respuesta(
    mensaje: str,
    telefono: str,
    historial: list[dict] | None = None,
    herramientas: list | None = None, # kept for signature compat, but not used directly here
    timeout_segundos: float = None,
) -> str:
    """Genera respuesta usando LangChain Tool Calling Agent con circuit breaker."""
    if timeout_segundos is None:
        timeout_segundos = GEMINI_TIMEOUT_SECONDS
    if historial is None:
        historial = []

    has_existing_case = False
    try:
        from .db import SyncSession, Radicado
        with SyncSession() as session:
            existing_radicado = session.query(Radicado).filter(Radicado.telefono == telefono).first()
            if existing_radicado:
                has_existing_case = True
    except Exception as e:
        logger.warning("Error al consultar caso existente para %s: %s", telefono, e)

    sys_inst = SYSTEM_PROMPT + f"\n\nFecha de hoy: {datetime.now().strftime('%Y-%m-%d')}."
    if has_existing_case:
        sys_inst += "\n\nNOTA DE CONTEXTO REAL: El cliente ya tiene un caso/radicado registrado. NO le solicites sus datos bsicos de contacto (nombre, empresa, correo, ciudad) ni identificacin, procede directamente con sus consultas."

    texto_usuario = _sanitizar_input(mensaje)

    texto = None
    tiempo_inicio = None
    
    # Preparamos las herramientas de LangChain y atamos el LLM
    lc_tools = _get_lc_tools(telefono)
    llm_with_tools = llm.bind_tools(lc_tools)
    
    from langgraph.prebuilt import create_react_agent
    agent_executor = create_react_agent(llm, lc_tools)
    
    messages = _historial_a_lc_messages(historial, sys_inst)
    messages.append(HumanMessage(content=texto_usuario))
    
    for intento in range(2):
        try:
            import time as time_module
            tiempo_inicio = time_module.time()

            def _send_with_cb():
                wrapped = _circuit_breaker_gemini(
                    lambda: agent_executor.invoke({"messages": messages})
                )
                return wrapped()

            result = await asyncio.wait_for(
                asyncio.to_thread(_send_with_cb),
                timeout=timeout_segundos
            )
            
            if isinstance(result, str):
                texto = result
            else:
                last_content = result["messages"][-1].content
                if isinstance(last_content, list):
                    texto = " ".join([b.get("text", "") for b in last_content if isinstance(b, dict) and "text" in b])
                else:
                    texto = str(last_content)

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
            logger.warning("Timeout en Gemini para %s despus de %.1fs", telefono, timeout_segundos)
            break
        except Exception as e:
            demobot_errors_total.labels(error_type="gemini_exception").inc()
            logger.error("Fallo inesperado generando respuesta para %s: %s", telefono, e)
            if "429" in str(e) and intento == 0:
                demobot_errors_total.labels(error_type="gemini_rate_limit").inc()
                await asyncio.sleep(5.0)
                continue
            break

    if not texto:
        nombre = telefono
        try:
            from .db import SyncSession, Contacto
            with SyncSession() as session:
                contacto = session.get(Contacto, telefono)
                if contacto and contacto.nombre:
                    nombre = contacto.nombre
        except Exception as db_err:
            logger.error("No se pudo consultar el nombre en DB para auto-escalar: %s", db_err)

        try:
            from . import tools
            tools.escalar_a_humano(
                telefono=telefono,
                nombre=nombre,
                resumen_caso="Fallo en el servicio conversacional (Gemini API fuera de servicio, timeout o lmite de cuota).",
                area="soporte"
            )
        except Exception as esc_err:
            logger.error("Fallo al auto-escalar conversacin tras error de Gemini: %s", esc_err)

        texto = _get_fallback_message()

    return texto


async def clasificar_intencion(texto: str) -> str:
    """Classify intent from user message into 'comercial', 'soporte' or 'otro'."""
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content="Clasifica el siguiente mensaje en una sola palabra: 'comercial', 'soporte' u 'otro'. Responde unicamente con esa palabra."),
                HumanMessage(content=texto)
            ]
        )
        content = response.content
        if isinstance(content, list):
            content = " ".join([b.get("text", "") for b in content if isinstance(b, dict) and "text" in b])
        tipo = str(content).strip().lower()
        if tipo not in ["comercial", "soporte", "otro"]:
            return "otro"
        return tipo
    except Exception as e:
        logger.error("Fallo clasificando intencion: %s", e)
        return "otro"

