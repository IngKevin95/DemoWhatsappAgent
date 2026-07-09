import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

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

proveedor = obtener_proveedor()
logger = logging.getLogger(__name__)

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
    tarea = asyncio.create_task(_revisar_inactividad())
    yield
    tarea.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"status": "SysBot activo"}


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
    respuesta = await generar_respuesta(mensaje.telefono, mensaje.texto, historial)

    await guardar_mensaje(mensaje.telefono, "user", mensaje.texto)
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
