"""Herramientas (CRM, Calendar, soporte, escalamiento). Precios/ofertas leen
de Postgres (editable desde NocoDB); Calendar y correo usan Google APIs
reales. CRM (leads/casos) usa EspoCRM vía API REST; licencias/soporte
consultan Firebird directamente. Ambos viven en infra de demo separada
(docker-compose.demo.yml) y degradan con gracia si no está levantada."""

import logging
import os
import random
import threading
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import firebird.driver as fb
import httpx

from .db import Agente, Area, Cliente, ColaEspera, Contacto, Modulo, Oferta, Parametro, SyncSession
from .integrations import espocrm
from .integrations.google import crear_evento_calendar, enviar_email, horarios_libres

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"
EMAIL_SOPORTE = os.getenv("EMAIL_SOPORTE", "soporte@sysplus.com")

# ponytail: mismo patrón sync de agent/providers/meta.py, duplicado a propósito
# porque tools.py corre sync y el proveedor async vive en la capa del webhook.
_META_TOKEN = os.getenv("META_ACCESS_TOKEN")
_META_PHONE_ID = os.getenv("META_PHONE_NUMBER_ID")
_META_API_URL = f"https://graph.facebook.com/v20.0/{_META_PHONE_ID}/messages"


def _enviar_whatsapp_directo(telefono: str, texto: str) -> None:
    httpx.post(
        _META_API_URL,
        headers={"Authorization": f"Bearer {_META_TOKEN}", "Content-Type": "application/json"},
        json={"messaging_product": "whatsapp", "to": telefono, "type": "text", "text": {"body": texto}},
    )

_CITAS_DB: list[dict] = []
_CITAS_LOCK = threading.Lock()  # ponytail: evita doble-agendar el mismo cupo entre threads concurrentes

FIREBIRD_HOST = os.getenv("FIREBIRD_HOST", "localhost")
FIREBIRD_PASSWORD = os.getenv("ISC_PASSWORD", "sysbot")


def cargar_info_negocio() -> str:
    return "\n\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(KNOWLEDGE_DIR.glob("*.md"))
    )


def buscar_en_knowledge(modulo: str) -> str:
    contenido = cargar_info_negocio()
    bloques = contenido.split("## ")
    for bloque in bloques:
        if bloque.lower().startswith(modulo.lower()):
            return "## " + bloque.strip()
    with SyncSession() as session:
        nombres = [m.nombre for m in session.query(Modulo).all()]
    return f"No encontré información específica sobre '{modulo}'. Módulos disponibles: {', '.join(nombres)}."


def _oferta_activa(session, modulo_id: int) -> Oferta | None:
    hoy = date.today()
    return (
        session.query(Oferta)
        .filter(
            Oferta.modulo_id == modulo_id,
            Oferta.activo.is_(True),
            Oferta.fecha_inicio <= hoy,
            Oferta.fecha_fin >= hoy,
        )
        .first()
    )


def consultar_precio_modulo(modulo: str) -> dict:
    with SyncSession() as session:
        mod = session.query(Modulo).filter(Modulo.nombre.ilike(modulo)).first()
        if not mod:
            return {"error": f"Módulo '{modulo}' no encontrado."}
        oferta = _oferta_activa(session, mod.id)
        if not oferta:
            return {"modulo": mod.nombre, "precio_mensual_cop": mod.precio_mensual_cop, "moneda": "COP"}
        precio_final = round(mod.precio_mensual_cop * (1 - oferta.descuento_pct / 100))
        return {
            "modulo": mod.nombre,
            "precio_mensual_cop": precio_final,
            "precio_regular_cop": mod.precio_mensual_cop,
            "descuento_pct": oferta.descuento_pct,
            "moneda": "COP",
        }


def consultar_ofertas_activas() -> list[dict]:
    hoy = date.today()
    with SyncSession() as session:
        ofertas = (
            session.query(Oferta, Modulo)
            .join(Modulo, Oferta.modulo_id == Modulo.id)
            .filter(Oferta.activo.is_(True), Oferta.fecha_inicio <= hoy, Oferta.fecha_fin >= hoy)
            .all()
        )
    return [
        {
            "modulo": modulo.nombre,
            "descuento_pct": oferta.descuento_pct,
            "precio_final_cop": round(modulo.precio_mensual_cop * (1 - oferta.descuento_pct / 100)),
            "vigente_hasta": oferta.fecha_fin.isoformat(),
        }
        for oferta, modulo in ofertas
    ]


def consultar_parametro(clave: str) -> dict:
    """Consulta un parámetro de configuración editable (horario de atención, email de soporte, etc)."""
    with SyncSession() as session:
        param = session.query(Parametro).filter(Parametro.clave == clave).first()
        if not param:
            return {"error": f"Parámetro '{clave}' no encontrado."}
        return {"clave": param.clave, "valor": param.valor}


def registrar_lead_crm(nombre: str, telefono: str, empresa: str, interes: str) -> dict:
    try:
        lead = espocrm.crear_lead(nombre, telefono, empresa, "", interes)
        return {"lead_id": lead.get("id"), "estado": "registrado"}
    except httpx.HTTPError as e:
        return {"estado": "error", "mensaje": f"CRM no disponible: {e}"}


def consultar_estado_cliente(telefono: str) -> dict:
    try:
        lead = espocrm.consultar_lead(telefono)
    except httpx.HTTPError as e:
        return {"estado": "error", "mensaje": f"CRM no disponible: {e}"}
    if not lead:
        return {"estado": "no_encontrado", "mensaje": "No hay registro previo en el CRM para este número."}
    return lead


def consultar_licencia(identificacion: str) -> dict:
    """Consulta si una cédula/NIT tiene licencia y contrato de soporte activo en Firebird.
    Llamar antes de crear un ticket o escalar un caso a soporte."""
    dsn = f"{FIREBIRD_HOST}/3050:licencias.fdb"
    try:
        con = fb.connect(database=dsn, user="sysdba", password=FIREBIRD_PASSWORD)
    except Exception as e:
        return {"estado": "sin_licencia", "nota": f"Servicio de licencias no disponible: {e}"}
    try:
        cur = con.cursor()
        cur.execute(
            "SELECT MODULO, SOPORTE_ACTIVO, SOPORTE_HASTA FROM LICENCIAS WHERE IDENTIFICACION = ?",
            (identificacion,),
        )
        fila = cur.fetchone()
        if not fila:
            return {"estado": "sin_licencia"}
        modulo, soporte_activo, soporte_hasta = fila
        estado = "con_licencia_con_soporte" if soporte_activo else "con_licencia_sin_soporte"
        return {
            "estado": estado,
            "modulo": modulo,
            "soporte_hasta": soporte_hasta.isoformat() if soporte_hasta else None,
        }
    finally:
        con.close()


def _get_area(session, nombre: str) -> Area:
    """Resuelve un nombre de área (string libre del LLM) a su fila Area, creándola si no existe."""
    area = session.query(Area).filter(Area.nombre.ilike(nombre)).first()
    if not area:
        area = Area(nombre=nombre)
        session.add(area)
        session.flush()
    return area


def _agentes_por_area(session, area: str) -> list[Agente]:
    return (
        session.query(Agente)
        .join(Area, Agente.area_id == Area.id)
        .filter(Area.nombre.ilike(area), Agente.activo.is_(True))
        .order_by(Agente.id)
        .all()
    )


def _ocupados() -> set:
    """IDs de agentes con un contacto activo (atendido_por no nulo) ahora mismo."""
    with SyncSession() as session:
        return {aid for (aid,) in session.query(Contacto.atendido_por).filter(Contacto.atendido_por.isnot(None)).all()}


def _upsert_contacto(session, telefono: str, nombre: str) -> Contacto:
    contacto = session.get(Contacto, telefono)
    if not contacto:
        contacto = Contacto(telefono=telefono, nombre=nombre)
        session.add(contacto)
    else:
        contacto.nombre = nombre
    return contacto


def guardar_datos_contacto(
    telefono: str,
    nombre: str,
    empresa: str | None = None,
    correo: str | None = None,
    ciudad: str | None = None,
) -> dict:
    """Guarda/actualiza los datos básicos de quien escribe (nombre, empresa, correo, ciudad).
    Llamar apenas el usuario los dé, típicamente al inicio de la conversación."""
    with SyncSession() as session:
        contacto = _upsert_contacto(session, telefono, nombre)
        if empresa is not None:
            contacto.empresa = empresa
        if correo is not None:
            contacto.correo = correo
        if ciudad is not None:
            contacto.ciudad = ciudad
        session.commit()
        return {"telefono": telefono, "estado": "guardado"}


def agendar_cita(nombre: str, telefono: str, motivo: str, fecha: str, hora: str, area: str) -> dict:
    """Agenda una cita si el horario pedido está libre en el calendario de la primera
    persona disponible de esa área (según su rango horario propio). fecha: 'YYYY-MM-DD'.
    hora: 'HH:MM', debe ser una de HORARIOS_DISPONIBLES (09:00, 10:30, 14:00, 16:00).
    area: p.ej. 'comercial' o 'soporte'. Si nadie de esa área está libre, devuelve
    alternativas libres ese mismo día (unión de todas las personas del área)."""
    with SyncSession() as session:
        personas = _agentes_por_area(session, area)
    if not personas:
        return {"disponible": False, "mensaje": f"No hay nadie configurado para el área '{area}'."}

    alternativas: set[str] = set()
    # ponytail: lock evita que dos peticiones concurrentes (ahora posibles gracias al
    # to_thread en brain.py) vean el mismo cupo "libre" y lo agenden por duplicado.
    with _CITAS_LOCK:
        # ponytail: idempotencia — si el LLM vuelve a llamar agendar_cita para el mismo
        # teléfono/fecha/hora (p.ej. reinterpreta el contexto en un turno posterior),
        # devuelve la cita ya existente en vez de crear un duplicado.
        existente = next(
            (c for c in _CITAS_DB if c["telefono"] == telefono and c["fecha"] == fecha and c["hora"] == hora),
            None,
        )
        if existente:
            return existente

        for persona in personas:
            libres = horarios_libres(fecha, persona.email, persona.hora_inicio, persona.hora_fin)
            # ponytail: horarios_libres() consulta el Calendar real vía freebusy, que no
            # lanza error ni refleja huecos si el service account no tiene acceso al
            # calendario (ver crear_evento_calendar) — _CITAS_DB es la fuente de verdad
            # de respaldo para no doble-agendar aunque el Calendar esté mal configurado.
            ocupadas_local = {c["hora"] for c in _CITAS_DB if c["atendido_email"] == persona.email and c["fecha"] == fecha}
            libres = [h for h in libres if h not in ocupadas_local]
            alternativas.update(libres)
            if hora in libres:
                cita_id = str(uuid.uuid4())[:8]
                cita = {
                    "cita_id": cita_id, "nombre": nombre, "telefono": telefono,
                    "motivo": motivo, "fecha": fecha, "hora": hora,
                    "area": area, "atendido_por": persona.nombre, "atendido_email": persona.email,
                }
                _CITAS_DB.append(cita)
                try:
                    evento = crear_evento_calendar(nombre, telefono, motivo, fecha, hora, persona.email)
                    cita["calendar_link"] = evento.get("htmlLink")
                except Exception as e:
                    # ponytail: nunca dejar esto en silencio — sin log, una cita "exitosa" para
                    # el cliente puede no existir realmente en el calendario del agente.
                    logger.exception("crear_evento_calendar falló para cita_id=%s email=%s", cita_id, persona.email)
                    cita["calendar_error"] = str(e)
                try:
                    reunion = espocrm.crear_reunion(nombre, telefono, motivo, fecha, hora)
                    cita["crm_meeting_id"] = reunion.get("id")
                except httpx.HTTPError as e:
                    cita["crm_meeting_error"] = str(e)
                return cita

    libres = sorted(alternativas)
    return {
        "disponible": False,
        "alternativas": libres,
        "mensaje": (
            f"El horario {hora} del {fecha} no está disponible en el área '{area}'."
            + (f" Libres ese día: {', '.join(libres)}." if libres else " No hay horarios libres ese día, prueba otra fecha.")
        ),
    }


def consultar_disponibilidad_agenda(area: str) -> list[dict]:
    """Horarios realmente libres (unión de todas las personas activas del área,
    respetando el rango horario de cada una) para los próximos 5 días."""
    with SyncSession() as session:
        personas = _agentes_por_area(session, area)
    dias = [(datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, 6)]
    resultado = []
    for d in dias:
        libres: set[str] = set()
        for persona in personas:
            libres.update(horarios_libres(d, persona.email, persona.hora_inicio, persona.hora_fin))
        resultado.append({"fecha": d, "horarios_libres": sorted(libres)})
    return resultado


def crear_ticket_soporte(telefono: str, descripcion: str, modulo: str) -> dict:
    try:
        caso = espocrm.crear_caso(telefono, descripcion, modulo)
        return {"ticket_id": caso.get("id"), "estado": "abierto"}
    except httpx.HTTPError as e:
        return {"estado": "error", "mensaje": f"CRM no disponible: {e}"}


def consultar_ticket_soporte(ticket_id: str) -> dict:
    try:
        return espocrm.consultar_caso(ticket_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"error": "no encontrado", "mensaje": f"No existe ningún ticket con ID {ticket_id}."}
        return {"error": f"CRM no disponible: {e}"}
    except httpx.HTTPError as e:
        return {"error": f"CRM no disponible: {e}"}


def crear_tarea(nombre: str, descripcion: str, fecha_vencimiento: str | None = None) -> dict:
    """Crea una tarea interna de seguimiento en el CRM (p.ej. 'llamar mañana para confirmar
    contrato de soporte', 'enviar cotización'). fecha_vencimiento: 'YYYY-MM-DD', opcional."""
    try:
        tarea = espocrm.crear_tarea(nombre, descripcion, fecha_vencimiento)
        return {"tarea_id": tarea.get("id"), "estado": "creada"}
    except httpx.HTTPError as e:
        return {"estado": "error", "mensaje": f"CRM no disponible: {e}"}


def escalar_a_humano(telefono: str, nombre: str, resumen_caso: str, area: str) -> dict:
    """Escala la conversación a un agente humano del área dada. Busca el primer agente
    del área que NO esté ya conectado con otro cliente. Si es de opción B (mismo
    WhatsApp del bot), lo conecta y el bot se pausa para este cliente. Si es de
    opción A, le notifica el caso por WhatsApp aparte (no se pausa). Si todos los
    agentes del área están ocupados, encola al cliente e informa su posición.
    Siempre registra el caso por correo a EMAIL_SOPORTE."""
    caso_id = f"ESC-{random.randint(1000, 9999)}"
    cuerpo = f"Cliente: {nombre}\nTeléfono: {telefono}\nResumen: {resumen_caso}"
    try:
        enviar_email(EMAIL_SOPORTE, f"[{caso_id}] Escalamiento SysBot - {nombre}", cuerpo)
        email_enviado = True
    except Exception:
        email_enviado = False

    with SyncSession() as session:
        agentes = _agentes_por_area(session, area)
        numero_bot = session.query(Parametro).filter(Parametro.clave == "whatsapp_numero_bot").first()
        if not agentes:
            return {
                "caso_id": caso_id, "estado": "escalado", "modo": None, "atendido_por": None,
                "email_enviado": email_enviado,
                "mensaje": f"Caso {caso_id} registrado, pero no hay agentes configurados para el área '{area}'.",
            }

        ocupados = _ocupados()
        libres = [a for a in agentes if a.id not in ocupados]
        if libres:
            agente = libres[0]
            if agente.telefono and numero_bot and agente.telefono == numero_bot.valor:
                modo = "conectado"
                contacto = _upsert_contacto(session, telefono, nombre)
                contacto.atendido_por = agente.id
                contacto.conectado_en = datetime.now(timezone.utc)
                session.commit()
                mensaje = (
                    f"Caso {caso_id} registrado. Un asesor humano de SysPlus dará "
                    f"seguimiento a {nombre} ({telefono}). Resumen: {resumen_caso}"
                )
            elif agente.telefono:
                # opción A: agente tiene número propio (distinto del bot) -> le
                # llega el resumen por WhatsApp aparte y se le pasa al usuario
                # un link directo wa.me para que pueda escribirle sin esperar.
                modo = "notificacion_con_contacto"
                _enviar_whatsapp_directo(
                    agente.telefono,
                    f"[{caso_id}] Nuevo caso de {nombre} ({telefono}) - área {area}\n{resumen_caso}",
                )
                link_agente = f"https://wa.me/{agente.telefono.lstrip('+')}"
                mensaje = (
                    f"Caso {caso_id} registrado y enviado a {agente.nombre}, quien dará "
                    f"seguimiento a tu caso. Resumen enviado: {resumen_caso}\n"
                    f"También puedes escribirle directamente aquí: {link_agente}"
                )
            else:
                # sin teléfono de agente configurado -> no hay a quién notificar
                # ni link que dar; el caso ya quedó por correo a EMAIL_SOPORTE.
                modo = "notificacion"
                mensaje = (
                    f"Caso {caso_id} registrado. Un asesor de SysPlus se comunicará contigo "
                    f"a la brevedad posible. Resumen: {resumen_caso}"
                )
            return {
                "caso_id": caso_id, "estado": "escalado", "modo": modo, "atendido_por": agente.nombre,
                "email_enviado": email_enviado,
                "mensaje": mensaje,
            }

        # todos ocupados -> cola
        _upsert_contacto(session, telefono, nombre)
        area_row = _get_area(session, area)
        delante = (
            session.query(ColaEspera)
            .filter(ColaEspera.area_id == area_row.id, ColaEspera.hasta.is_(None))
            .count()
        )
        espera = session.get(ColaEspera, telefono)
        if espera:
            espera.area_id = area_row.id
            espera.desde = datetime.now(timezone.utc)
            espera.hasta = None
        else:
            session.add(ColaEspera(telefono=telefono, area_id=area_row.id))
        session.commit()
        return {
            "caso_id": caso_id, "estado": "en_cola", "posicion": delante + 1,
            "email_enviado": email_enviado,
            "mensaje": (
                f"Caso {caso_id} registrado. Todos los agentes de '{area}' están ocupados ahora mismo. "
                f"Hay {delante} persona(s) delante de ti, en breve te atenderán."
            ),
        }


def promover_colas() -> list[dict]:
    """Conecta clientes en cola con agentes de opción B que hayan quedado libres.
    Se llama en cada webhook (no hay scheduler). Devuelve [{telefono, mensaje}] a notificar."""
    promovidos = []
    with SyncSession() as session:
        numero_bot = session.query(Parametro).filter(Parametro.clave == "whatsapp_numero_bot").first()
        ocupados = _ocupados()
        areas = session.query(Area).join(ColaEspera, ColaEspera.area_id == Area.id).distinct().all()
        for area_row in areas:
            libres = [
                a for a in _agentes_por_area(session, area_row.nombre)
                if a.id not in ocupados and a.telefono and numero_bot and a.telefono == numero_bot.valor
            ]
            cola = (
                session.query(ColaEspera)
                .filter(ColaEspera.area_id == area_row.id, ColaEspera.hasta.is_(None))
                .order_by(ColaEspera.desde)
                .all()
            )
            for agente, espera in zip(libres, cola):
                contacto = session.get(Contacto, espera.telefono)
                contacto.atendido_por = agente.id
                contacto.conectado_en = datetime.now(timezone.utc)
                ocupados.add(agente.id)
                espera.agente_id = agente.id
                espera.hasta = datetime.now(timezone.utc)
                promovidos.append({
                    "telefono": espera.telefono,
                    "mensaje": f"¡Ya te toca {contacto.nombre}! {agente.nombre} te va a atender ahora, un momento.",
                })
        session.commit()
    return promovidos


def registrar_cliente(telefono: str, numero_identificacion: str | None = None, nit_empresa: str | None = None) -> dict:
    """Marca un contacto existente como cliente confirmado, guardando su identificación
    (y la de su empresa, si aplica). Requiere que el contacto ya exista (se crea al
    escalar o al registrar_lead_crm)."""
    with SyncSession() as session:
        contacto = session.get(Contacto, telefono)
        if not contacto:
            return {"error": f"No hay contacto registrado con el teléfono {telefono}."}
        cliente = session.get(Cliente, telefono)
        if not cliente:
            cliente = Cliente(telefono=telefono)
            session.add(cliente)
        if numero_identificacion is not None:
            cliente.numero_identificacion = numero_identificacion
        if nit_empresa is not None:
            cliente.nit_empresa = nit_empresa
        session.commit()
        return {"telefono": telefono, "estado": "cliente_registrado"}
