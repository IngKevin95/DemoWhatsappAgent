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
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse, JSONResponse, Response
from sqlalchemy import select, text

from .brain import generar_respuesta
from .db import Contacto, Conversacion, Parametro, SyncSession
from .memory import (
    abrir_conversacion,
    guardar_mensaje,
    inicializar_db,
    limpiar_historial,
    obtener_conversacion_activa,
    obtener_historial,
    telefonos_con_actividad_reciente,
    ultimo_mensaje,
    Mensaje,
    SessionLocal,
)
from .providers import obtener_proveedor
from .tools import promover_colas
from .prometheus_metrics import (
    get_metrics, http_requests_total, http_request_duration_seconds,
    demobot_uptime_seconds, demobot_active_conversations, demobot_errors_total,
    demobot_dependency_health
)
from .scheduler import start_scheduler, stop_scheduler

proveedor_meta = obtener_proveedor("meta")
proveedor_telegram = obtener_proveedor("telegram")

def _obtener_proveedor_para_canal(canal: str):
    return proveedor_telegram if canal == "telegram" else proveedor_meta
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
                session.execute(text("SELECT 1"))
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
            # Usa el mismo SDK que brain.py (google.genai), no el deprecado.
            from google import genai
            model_name = os.getenv("MODEL_NAME", "gemini-3.1-flash-lite")
            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents="test",
            )
            return "ok" if response and response.text else "degraded"
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
            host = os.getenv("FIREBIRD_HOST", "firebird")
            port = os.getenv("FIREBIRD_PORT", "3050")
            db_file = os.getenv("FIREBIRD_DATABASE", "licencias.fdb")
            dsn = f"{host}/{port}:{db_file}"
            conn = connect(
                database=dsn,
                user=os.getenv("FIREBIRD_USER", "sysdba"),
                password=os.getenv("ISC_PASSWORD", "sysbot"),
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
MENSAJE_CHECKIN_1 = "Veo que te ocupaste un momento. ¿Hay algo más en lo que te pueda ayudar o sería todo por hoy?"
MENSAJE_CHECKIN_2 = "Aún sigo por aquí. Si no tienes más dudas en unos minutos, cerraré la conversación para organizar mi atención."
MENSAJE_CIERRE = (
    "Ha sido un gusto ayudarte. Cerraremos la sesión por inactividad. Si necesitas algo más luego, escríbeme de nuevo. ¡Que tengas un excelente día! 😊"
)


async def enviar_mensaje_seguro(telefono: str, texto: str, botones: list[dict] = None, canal: str = "meta") -> None:
    """enviar_mensaje sin dejar que un fallo (token vencido, rate limit, etc.) tumbe el webhook."""
    try:
        prov = _obtener_proveedor_para_canal(canal)
        await prov.enviar_mensaje(telefono, texto, botones=botones)
    except Exception:
        logger.exception("Fallo enviando mensaje a %s por canal %s", telefono, canal)


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
                async with SessionLocal() as session:
                    # SELECT ... FOR UPDATE serializa la revisión entre workers —
                    # solo un worker actúa por teléfono en cada ciclo.
                    result_conv = await session.execute(
                        select(Conversacion)
                        .where(Conversacion.telefono == telefono, Conversacion.estado == "abierta")
                        .order_by(Conversacion.id.desc())
                        .limit(1)
                        .with_for_update(skip_locked=True)
                    )
                    conv = result_conv.scalars().first()
                    if not conv:
                        continue  # otro worker ya lo está procesando o no hay conv abierta

                    # Último mensaje
                    result_msg = await session.execute(
                        select(Mensaje)
                        .where(Mensaje.telefono == telefono)
                        .order_by(Mensaje.timestamp.desc())
                        .limit(1)
                    )
                    m = result_msg.scalars().first()
                    if not m:
                        continue

                    segundos = _segundos_desde(m.timestamp)
                    contacto = await session.get(Contacto, telefono)
                    canal = contacto.canal if contacto else "meta"

                    if (m.role == "user" or (m.role == "assistant" and m.content not in (MENSAJE_CHECKIN_1, MENSAJE_CHECKIN_2, MENSAJE_CIERRE))) and segundos > CHECKIN_INACTIVIDAD_SEGUNDOS:
                        session.add(Mensaje(telefono=telefono, role="assistant", content=MENSAJE_CHECKIN_1, conversacion_id=conv.id))
                        await session.commit()
                        await enviar_mensaje_seguro(telefono, MENSAJE_CHECKIN_1, canal=canal)

                    elif m.role == "assistant" and m.content == MENSAJE_CHECKIN_1 and segundos > CHECKIN_INACTIVIDAD_SEGUNDOS:
                        session.add(Mensaje(telefono=telefono, role="assistant", content=MENSAJE_CHECKIN_2, conversacion_id=conv.id))
                        await session.commit()
                        await enviar_mensaje_seguro(telefono, MENSAJE_CHECKIN_2, canal=canal)

                    elif m.role == "assistant" and m.content == MENSAJE_CHECKIN_2 and segundos > CIERRE_INACTIVIDAD_SEGUNDOS:
                        # 1. Guardar MENSAJE_CIERRE primero (flush separado para evitar
                        #    que el autoflush lo incluya en el DELETE posterior).
                        session.add(Mensaje(telefono=telefono, role="assistant", content=MENSAJE_CIERRE, conversacion_id=conv.id))
                        await session.flush()

                        # 2. Borrar todo el historial excepto el MENSAJE_CIERRE que acabamos de insertar.
                        del_result = await session.execute(
                            select(Mensaje)
                            .where(Mensaje.telefono == telefono, Mensaje.content != MENSAJE_CIERRE)
                        )
                        for msg_to_del in del_result.scalars().all():
                            await session.delete(msg_to_del)

                        # 3. Cerrar la conversación.
                        conv.estado = "cerrada"
                        conv.motivo_cierre = "inactividad"
                        if conv.espera_desde and not conv.espera_hasta:
                            conv.espera_hasta = datetime.now(timezone.utc).replace(tzinfo=None)

                        await session.commit()
                        await enviar_mensaje_seguro(telefono, MENSAJE_CIERRE, canal=canal)
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

# Servir PDFs de fichas técnicas de módulos
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


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


async def procesar_mensaje_entrante(mensaje, request: Request = None, canal="meta"):
    if mensaje is None:
        return {"status": "ignorado"}

    with SyncSession() as session:
        contacto = session.query(Contacto).filter(Contacto.telefono == mensaje.telefono).first()
        es_nuevo = contacto is None
        if not contacto:
            contacto = Contacto(telefono=mensaje.telefono, nombre=mensaje.nombre or mensaje.telefono, consentimiento_datos=False, canal=canal)
            session.add(contacto)
            session.commit()
            session.refresh(contacto)
        consentimiento_dado = contacto.consentimiento_datos

    if not consentimiento_dado:
        texto_upper = mensaje.texto.strip().upper()
        if texto_upper == "SI":
            with SyncSession() as session:
                contacto = session.query(Contacto).filter(Contacto.telefono == mensaje.telefono).first()
                contacto.consentimiento_datos = True
                session.commit()
            try:
                import asyncio
                from .tools import _sync_lead_crm
                # usa el nombre real del contacto (no un genérico que colisiona en el CRM)
                await asyncio.to_thread(_sync_lead_crm, mensaje.telefono, "Lead Habeas Data")
            except Exception as e:
                logger.error("No se pudo crear lead automático: %s", e)
            await enviar_mensaje_seguro(mensaje.telefono, "Gracias. Hemos registrado tu consentimiento. ¿En qué te puedo ayudar?", canal=canal)
            await abrir_conversacion(mensaje.telefono)
            return {"status": "ok"}
        elif texto_upper == "NO":
            await enviar_mensaje_seguro(mensaje.telefono, "Entendemos. No podemos procesar tus datos sin tu consentimiento. Hasta pronto.", canal=canal)
            return {"status": "ok"}
        else:
            botones = [
                {"id": "SI", "title": "Sí, acepto"},
                {"id": "NO", "title": "No, gracias"}
            ]
            saludo = "¡Hola! Soy SysBot, el asesor virtual de SysPlus. " if es_nuevo else ""
            await enviar_mensaje_seguro(
                mensaje.telefono,
                saludo + "Por políticas de privacidad (Habeas Data), necesitamos tu consentimiento para procesar tus datos. Por favor elige una opción.",
                botones=botones,
                canal=canal
            )
            return {"status": "ok"}

    conversacion_id = await obtener_conversacion_activa(mensaje.telefono)
    if not conversacion_id:
        conversacion_id = await abrir_conversacion(mensaje.telefono)

    with SyncSession() as session:
        from .db import Conversacion
        conv = session.query(Conversacion).get(conversacion_id)
        # reclasifica mientras siga sin definir u "otro": el 1er mensaje suele ser un
        # saludo/datos ("otro"); el interés real (comercial/soporte) llega después.
        if conv and conv.tipo_solicitud in (None, "otro"):
            from .brain import clasificar_intencion
            # se clasifica asincronamente
            tipo = await clasificar_intencion(mensaje.texto)
            conv.tipo_solicitud = tipo
            session.commit()

    for promovido in promover_colas():
        conv_id = await obtener_conversacion_activa(promovido["telefono"])
        await guardar_mensaje(promovido["telefono"], "assistant", promovido["mensaje"], conversacion_id=conv_id)
        
        with SyncSession() as session:
            contacto = session.query(Contacto).filter(Contacto.telefono == promovido["telefono"]).first()
            canal = contacto.canal if contacto else "meta"
            
        await enviar_mensaje_seguro(promovido["telefono"], promovido["mensaje"], canal=canal)

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
        await guardar_mensaje(mensaje.telefono, "user", mensaje.texto, conversacion_id=conversacion_id)
        return {"status": "conectado"}

    historial = await obtener_historial(mensaje.telefono)
    # Sanitize user input before processing
    mensaje_sanitizado = sanitize_input(mensaje.texto)
    respuesta = await generar_respuesta(
        mensaje=mensaje_sanitizado,
        telefono=mensaje.telefono,
        historial=historial
    )

    if "/static/pdfs/" in respuesta:
        # Usar PUBLIC_BASE_URL si está configurado (URL pública del tunnel/proxy).
        # Fallback a request.base_url solo si no hay otra opción.
        public_base = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
        if not public_base and request:
            public_base = str(request.base_url).rstrip("/")
        if public_base:
            respuesta = respuesta.replace(f"{public_base}/static/pdfs/", "/static/pdfs/")
            respuesta = respuesta.replace("/static/pdfs/", f"{public_base}/static/pdfs/")

    await guardar_mensaje(mensaje.telefono, "user", mensaje_sanitizado, conversacion_id=conversacion_id)
    await guardar_mensaje(mensaje.telefono, "assistant", respuesta, conversacion_id=conversacion_id)

    # Si la respuesta incluye un link a PDF, extraerlo y enviarlo como documento
    # para que WhatsApp lo muestre como archivo descargable (type: document).
    import re as _re
    pdf_matches = _re.findall(r'https?://[^\s\)]+\.pdf', respuesta)
    if pdf_matches and canal == "meta":
        # Texto de acompañamiento: la respuesta sin los links markdown
        texto_sin_links = _re.sub(r'\[([^\]]+)\]\(https?://[^\)]+\.pdf\)', r'\1', respuesta)
        texto_sin_links = _re.sub(r'https?://[^\s]+\.pdf', '', texto_sin_links).strip()

        if texto_sin_links:
            await enviar_mensaje_seguro(mensaje.telefono, texto_sin_links, canal=canal)

        for pdf_url in pdf_matches:
            nombre_archivo = pdf_url.split("/")[-1]
            try:
                prov = _obtener_proveedor_para_canal(canal)
                await prov.enviar_mensaje(
                    mensaje.telefono,
                    texto="",
                    documento={
                        "link": pdf_url,
                        "filename": nombre_archivo,
                    }
                )
            except Exception:
                logger.exception("Fallo enviando documento PDF %s a %s", pdf_url, mensaje.telefono)
    else:
        await enviar_mensaje_seguro(mensaje.telefono, respuesta, canal=canal)
    return {"status": "ok"}


@app.get("/webhook")
async def verificar_webhook(request: Request):
    challenge = proveedor_meta.validar_webhook(dict(request.query_params))
    if challenge:
        return PlainTextResponse(challenge)
    return PlainTextResponse("Token inválido", status_code=403)


@app.post("/webhook")
async def recibir_webhook(request: Request):
    cuerpo = await request.body()
    firma = request.headers.get("X-Hub-Signature-256")
    if not proveedor_meta.validar_firma(cuerpo, firma):
        return PlainTextResponse("Firma inválida", status_code=403)

    payload = await request.json()
    mensaje = proveedor_meta.parsear_webhook(payload)
    if mensaje is None:
        return {"status": "ignorado"}
    
    return await procesar_mensaje_entrante(mensaje, request=request, canal="meta")



@app.get("/webhook/telegram")
async def verificar_webhook_telegram(request: Request):
    challenge = proveedor_telegram.validar_webhook(dict(request.query_params))
    if challenge:
        return PlainTextResponse(challenge)
    return PlainTextResponse("Token inválido", status_code=403)

@app.post("/webhook/telegram")
async def recibir_webhook_telegram(request: Request):
    cuerpo = await request.body()
    firma = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if not proveedor_telegram.validar_firma(cuerpo, firma):
        return PlainTextResponse("Firma inválida", status_code=403)

    payload = await request.json()
    mensaje = proveedor_telegram.parsear_webhook(payload)
    if mensaje is None:
        return {"status": "ignorado"}
        
    return await procesar_mensaje_entrante(mensaje, request=request, canal="telegram")

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

    conv_id = await obtener_conversacion_activa(telefono_cliente)
    if not conv_id:
        conv_id = await abrir_conversacion(telefono_cliente)

    await guardar_mensaje(telefono_cliente, "assistant", MENSAJE_REACTIVACION, conversacion_id=conv_id)
    with SyncSession() as session:
        contacto = session.query(Contacto).filter(Contacto.telefono == telefono_cliente).first()
        canal = contacto.canal if contacto else "meta"
        
    await enviar_mensaje_seguro(telefono_cliente, MENSAJE_REACTIVACION, canal=canal)
    return {"status": "cerrado"}
