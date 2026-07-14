import asyncio
import hmac
import hashlib
import json
import logging
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, JSONResponse, Response

from .brain import generar_respuesta
from .db import Contacto, Parametro, SyncSession
from .memory import (
    guardar_mensaje,
    inicializar_db,
    limpiar_historial,
    obtener_historial,
    telefonos_con_actividad_reciente,
    ultimo_mensaje,
)
from .providers import obtener_proveedor
from .tools import promover_colas
from .prometheus_metrics import (
    get_metrics, http_requests_total, http_request_duration_seconds,
    demobot_uptime_seconds, demobot_active_conversations, demobot_errors_total,
    demobot_dependency_health
)
from .scheduler import start_scheduler, stop_scheduler

proveedor = obtener_proveedor()
logger = logging.getLogger(__name__)

# App startup tracking (for /health endpoint)
_app_start_time = datetime.now(timezone.utc)

# Secrets to scrub from logs
_SECRETS_PATTERNS = [
    r'DATABASE_URL=[^\s]+',
    r'GOOGLE_CLIENT_ID=[^\s]+',
    r'GOOGLE_CLIENT_SECRET=[^\s]+',
    r'META_API_TOKEN=[^\s]+',
    r'FIREBIRD_PASSWORD=[^\s]+',
    r'postgresql://[^\s]+',
]


def scrub_secrets(message: str) -> str:
    """Scrub sensitive credentials from log messages."""
    scrubbed = message
    for pattern in _SECRETS_PATTERNS:
        scrubbed = re.sub(pattern, '***REDACTED***', scrubbed, flags=re.IGNORECASE)
    return scrubbed


def sanitize_input(user_input: str) -> str:
    """Sanitize user input to prevent XSS and SQL injection."""
    if not user_input:
        return user_input

    # Remove script tags and event handlers
    sanitized = re.sub(r'<script[^>]*>.*?</script>', '', user_input, flags=re.IGNORECASE | re.DOTALL)
    sanitized = re.sub(r'\bon\w+\s*=', '', sanitized, flags=re.IGNORECASE)

    # Remove dangerous SQL keywords at start of input
    dangerous_sql = r'\b(DROP|DELETE|TRUNCATE|INSERT|UPDATE|ALTER|CREATE|EXEC)\b'
    sanitized = re.sub(dangerous_sql, '', sanitized, flags=re.IGNORECASE)

    return sanitized


async def probe_postgres(timeout: int = 3) -> str:
    """Probe PostgreSQL connectivity with timeout. Returns 'ok', 'degraded', or 'error'."""
    try:
        async with asyncio.timeout(timeout):
            with SyncSession() as session:
                session.execute("SELECT 1")
                return "ok"
    except asyncio.TimeoutError:
        logger.warning("Postgres probe timeout after %ds", timeout)
        return "degraded"
    except Exception as e:
        logger.error("Postgres probe failed: %s", str(e))
        return "error"


async def probe_gemini(timeout: int = 5) -> str:
    """Probe Gemini API availability with timeout. Returns 'ok', 'degraded', or 'error'."""
    try:
        async with asyncio.timeout(timeout):
            # Simple test: verify API key and model availability
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))
            model = genai.GenerativeModel("gemini-1.5-flash")
            # Quick test: generate minimal response
            response = model.generate_content("test", stream=False)
            return "ok" if response else "degraded"
    except asyncio.TimeoutError:
        logger.warning("Gemini probe timeout after %ds", timeout)
        return "degraded"
    except Exception as e:
        logger.error("Gemini probe failed: %s", str(e))
        return "error"


async def probe_espocrm(timeout: int = 5) -> str:
    """Probe EspoCRM API availability with timeout. Returns 'ok', 'degraded', or 'error'."""
    try:
        async with asyncio.timeout(timeout):
            import httpx
            espocrm_url = os.getenv("ESPOCRM_URL", "http://espocrm")
            api_key = os.getenv("ESPOCRM_API_KEY", "")
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{espocrm_url}/api/v1/App/info",
                    headers={"X-Api-Key": api_key},
                    timeout=timeout
                )
                return "ok" if response.status_code == 200 else "degraded"
    except asyncio.TimeoutError:
        logger.warning("EspoCRM probe timeout after %ds", timeout)
        return "degraded"
    except Exception as e:
        logger.error("EspoCRM probe failed: %s", str(e))
        return "error"


async def probe_firebird(timeout: int = 3) -> str:
    """Probe Firebird database connectivity with timeout. Returns 'ok', 'degraded', or 'error'."""
    try:
        async with asyncio.timeout(timeout):
            from firebird.driver import connect
            conn = connect(
                host=os.getenv("FIREBIRD_HOST", "firebird"),
                port=int(os.getenv("FIREBIRD_PORT", 3050)),
                database=os.getenv("FIREBIRD_DATABASE", ""),
                user=os.getenv("FIREBIRD_USER", "sysdba"),
                password=os.getenv("FIREBIRD_PASSWORD", ""),
            )
            conn.close()
            return "ok"
    except asyncio.TimeoutError:
        logger.warning("Firebird probe timeout after %ds", timeout)
        return "degraded"
    except Exception as e:
        logger.error("Firebird probe failed: %s", str(e))
        return "error"

CHECKIN_INACTIVIDAD_SEGUNDOS = 300
CIERRE_INACTIVIDAD_SEGUNDOS = 300
MENSAJE_CHECKIN = "Veo que te ocupaste un momento. ¿Hay algo más en lo que te pueda ayudar o sería todo por hoy?"
MENSAJE_CIERRE = (
    "Ha sido un gusto ayudarte. Si necesitas algo más, aquí estaré con gusto "
    "para seguir apoyándote. ¡Que tengas un excelente día! 😊"
)


async def enviar_mensaje_seguro(telefono: str, texto: str) -> None:
    """enviar_mensaje sin dejar que un fallo (token vencido, rate limit, etc.) tumbe el webhook."""
    try:
        await proveedor.enviar_mensaje(telefono, texto)
    except Exception:
        logger.exception("Fallo enviando mensaje de WhatsApp a %s", telefono)


def _segundos_desde(ts: datetime) -> float:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - ts).total_seconds()


async def _revisar_inactividad():
    """Corre en background: si el usuario deja de responder, primero pregunta
    si hay algo más en qué ayudar; si tampoco responde a eso, cierra la charla."""
    while True:
        await asyncio.sleep(60)
        try:
            for telefono in await telefonos_con_actividad_reciente():
                m = await ultimo_mensaje(telefono)
                if not m:
                    continue
                segundos = _segundos_desde(m["timestamp"])
                if m["role"] == "user" and segundos > CHECKIN_INACTIVIDAD_SEGUNDOS:
                    await guardar_mensaje(telefono, "assistant", MENSAJE_CHECKIN)
                    await enviar_mensaje_seguro(telefono, MENSAJE_CHECKIN)
                elif (
                    m["role"] == "assistant"
                    and m["content"] == MENSAJE_CHECKIN
                    and segundos > CIERRE_INACTIVIDAD_SEGUNDOS
                ):
                    await guardar_mensaje(telefono, "assistant", MENSAJE_CIERRE)
                    await enviar_mensaje_seguro(telefono, MENSAJE_CIERRE)
                    await limpiar_historial(telefono)
        except Exception:
            logger.exception("Fallo revisando inactividad")


TIMEOUT_PAUSA_MINUTOS_DEFAULT = int(os.getenv("TIMEOUT_PAUSA_MINUTOS", "60"))
MENSAJE_REACTIVACION = "Retomo la conversación por aquí. ¿En qué te puedo ayudar?"


def _timeout_pausa_minutos(session) -> int:
    param = session.query(Parametro).filter(Parametro.clave == "timeout_pausa_minutos").first()
    if param and param.valor.isdigit():
        return int(param.valor)
    return TIMEOUT_PAUSA_MINUTOS_DEFAULT


@asynccontextmanager
async def lifespan(app: FastAPI):
    await inicializar_db()
    start_scheduler()  # Start background scheduler
    tarea = asyncio.create_task(_revisar_inactividad())
    yield
    tarea.cancel()
    stop_scheduler()  # Stop scheduler on shutdown


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"status": "SysBot activo"}


@app.get("/health")
async def health():
    """Health check endpoint: returns 200 with app status and real dependency probes."""
    global _app_start_time
    now = datetime.now(timezone.utc)
    uptime_seconds = int((now - _app_start_time).total_seconds())

    # Run all probes in parallel with asyncio
    postgres_status, gemini_status, espocrm_status, firebird_status = await asyncio.gather(
        probe_postgres(timeout=3),
        probe_gemini(timeout=5),
        probe_espocrm(timeout=5),
        probe_firebird(timeout=3),
        return_exceptions=False
    )

    return JSONResponse({
        "status": "healthy",
        "timestamp": now.isoformat().replace('+00:00', 'Z'),
        "uptime_seconds": uptime_seconds,
        "version": "v1.0.0",
        "dependencies": {
            "postgres": postgres_status,
            "gemini": gemini_status,
            "espocrm": espocrm_status,
            "firebird": firebird_status
        }
    })


@app.get("/ready")
async def ready():
    """Readiness probe: returns 200 if Postgres + Gemini are 'ok', 503 otherwise."""
    postgres_status = await probe_postgres(timeout=3)
    gemini_status = await probe_gemini(timeout=5)

    is_ready = postgres_status == "ok" and gemini_status == "ok"
    status_code = 200 if is_ready else 503

    return JSONResponse({
        "ready": is_ready
    }, status_code=status_code)


@app.get("/metrics", response_class=Response)
async def metrics():
    """Prometheus metrics endpoint: returns real instrumented metrics."""
    metrics_data = get_metrics()
    return Response(content=metrics_data, media_type="text/plain; charset=utf-8; version=0.0.4")


def validar_firma_meta(body: str, signature: str | None, verify_token: str) -> bool:
    """Validate Meta webhook signature (HMAC-SHA256).

    AC-4 Security: Reject unauthorized requests.
    """
    if not signature:
        return False

    try:
        # Expected format: sha256=<hex>
        algo, sig_hash = signature.split("=", 1)
        if algo != "sha256":
            return False

        expected_hash = hmac.new(
            verify_token.encode(),
            body.encode() if isinstance(body, str) else body,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(sig_hash, expected_hash)
    except (ValueError, AttributeError):
        return False


@app.get("/webhook")
async def verificar_webhook(request: Request):
    challenge = proveedor.validar_webhook(dict(request.query_params))
    if challenge:
        return PlainTextResponse(challenge)
    return PlainTextResponse("Token inválido", status_code=403)


@app.post("/webhook")
async def recibir_webhook(request: Request):
    cuerpo = await request.body()
    firma = request.headers.get("X-Hub-Signature-256")
    if not proveedor.validar_firma(cuerpo, firma):
        return PlainTextResponse("Firma inválida", status_code=403)

    payload = await request.json()
    mensaje = proveedor.parsear_webhook(payload)
    if mensaje is None:
        return {"status": "ignorado"}

    for promovido in promover_colas():
        await guardar_mensaje(promovido["telefono"], "assistant", promovido["mensaje"])
        await enviar_mensaje_seguro(promovido["telefono"], promovido["mensaje"])

    with SyncSession() as session:
        conectado = (
            session.query(Contacto)
            .filter(Contacto.telefono == mensaje.telefono, Contacto.atendido_por.isnot(None))
            .first()
        )
        if conectado:
            limite = timedelta(minutes=_timeout_pausa_minutos(session))
            conectado_en = conectado.conectado_en
            if conectado_en and conectado_en.tzinfo is None:
                conectado_en = conectado_en.replace(tzinfo=timezone.utc)
            expirado = conectado_en and (datetime.now(timezone.utc) - conectado_en > limite)
            if expirado:
                conectado.atendido_por = None
                conectado.conectado_en = None
                session.commit()
                conectado = None
            else:
                conectado.conectado_en = datetime.now(timezone.utc)
                session.commit()
    if conectado:
        await guardar_mensaje(mensaje.telefono, "user", mensaje.texto)
        return {"status": "conectado"}

    historial = await obtener_historial(mensaje.telefono)
    # Sanitize user input before processing
    mensaje_sanitizado = sanitize_input(mensaje.texto)
    respuesta = await generar_respuesta(
        mensaje=mensaje_sanitizado,
        telefono=mensaje.telefono,
        historial=historial
    )

    await guardar_mensaje(mensaje.telefono, "user", mensaje_sanitizado)
    await guardar_mensaje(mensaje.telefono, "assistant", respuesta)

    await enviar_mensaje_seguro(mensaje.telefono, respuesta)
    return {"status": "ok"}


@app.post("/agentes/{telefono_cliente}/liberar")
async def liberar_agente(telefono_cliente: str):
    """El agente humano llama esto (o se automatiza desde NocoDB, vaciando atendido_por)
    para devolver la conversación al bot antes del timeout automático."""
    with SyncSession() as session:
        conectado = (
            session.query(Contacto)
            .filter(Contacto.telefono == telefono_cliente, Contacto.atendido_por.isnot(None))
            .first()
        )
        if not conectado:
            return {"status": "no_conectado"}
        conectado.atendido_por = None
        conectado.conectado_en = None
        session.commit()

    await guardar_mensaje(telefono_cliente, "assistant", MENSAJE_REACTIVACION)
    await proveedor.enviar_mensaje(telefono_cliente, MENSAJE_REACTIVACION)
    return {"status": "cerrado"}
