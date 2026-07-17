"""Herramientas (CRM, Calendar, soporte, escalamiento). Precios/ofertas leen
de Postgres (editable desde NocoDB); Calendar y correo usan Google APIs
reales. CRM (leads/casos) usa EspoCRM vía API REST; licencias/soporte
consultan Firebird directamente. Ambos viven en infra de demo separada
(docker-compose.demo.yml) y degradan con gracia si no está levantada."""

import logging
import os
import threading
import unicodedata
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import firebird.driver as fb
import httpx

from .db import Agente, Area, Cliente, Contacto, Modulo, Oferta, Parametro, Radicado, SyncSession, Combo
from .integrations import espocrm
from .integrations.google import crear_evento_calendar, enviar_email, horarios_libres

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"
EMAIL_SOPORTE = os.getenv("EMAIL_SOPORTE", "soporte@sysplus.com")


def _norm(s: str) -> str:
    """minúsculas sin acentos, para matchear 'Nomina' con 'Nómina'."""
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()

# ponytail: mismo patrón sync de agent/providers/meta.py, duplicado a propósito
# porque tools.py corre sync y el proveedor async vive en la capa del webhook.
_META_TOKEN = os.getenv("META_ACCESS_TOKEN")
_META_PHONE_ID = os.getenv("META_PHONE_NUMBER_ID")
_META_API_URL = f"https://graph.facebook.com/v20.0/{_META_PHONE_ID}/messages"


def _enviar_whatsapp_directo(telefono: str, texto: str) -> None:
    resp = httpx.post(
        _META_API_URL,
        headers={"Authorization": f"Bearer {_META_TOKEN}", "Content-Type": "application/json"},
        json={"messaging_product": "whatsapp", "to": telefono, "type": "text", "text": {"body": texto}},
    )
    # Meta devuelve 200 aunque el número no esté en la lista de destinatarios
    # permitidos o esté fuera de la ventana de 24h: sin este chequeo el fallo era
    # invisible (por eso "el correo llegó pero el WhatsApp no").
    if resp.status_code >= 400:
        raise RuntimeError(f"Meta rechazó el WhatsApp a {telefono}: {resp.status_code} {resp.text[:200]}")


def _franjas_bd(hora_inicio: str, hora_fin: str) -> list[str]:
    """Franjas de 1h en [hora_inicio, hora_fin) según la ventana horaria del agente
    en la BD. Respaldo cuando el Calendar real no se puede consultar."""
    try:
        h = datetime.strptime(hora_inicio, "%H:%M")
        fin = datetime.strptime(hora_fin, "%H:%M")
    except (ValueError, TypeError):
        h = datetime.strptime("09:00", "%H:%M")
        fin = datetime.strptime("18:00", "%H:%M")
    out = []
    while h + timedelta(hours=1) <= fin:
        out.append(h.strftime("%H:%M"))
        h += timedelta(hours=1)
    return out

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
    objetivo = _norm(modulo)

    stop_words = {"de", "del", "el", "la", "un", "una", "y", "modulo", "manual", "documento", "ficha", "tecnica", "sobre", "para"}
    query_words = [w for w in objetivo.split() if w not in stop_words]
    if not query_words:
        query_words = [objetivo]

    matching_blocks = []
    for bloque in contenido.split("## "):
        if not bloque.strip():
            continue
        header = bloque.split("\n")[0]
        header_norm = _norm(header)

        is_match = False
        if objetivo in header_norm or header_norm in objetivo:
            is_match = True
        else:
            header_words = set(header_norm.split())
            if any(qw in header_words for qw in query_words):
                is_match = True

        if is_match:
            matching_blocks.append("## " + bloque.strip())

    if matching_blocks:
        resultado = "\n\n".join(matching_blocks)
        # Reemplazar paths relativos con la URL pública completa para que el LLM
        # tenga el link absoluto y pueda incluirlo directamente en su respuesta.
        public_base = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
        if public_base and "/static/pdfs/" in resultado:
            resultado = resultado.replace("/static/pdfs/", f"{public_base}/static/pdfs/")
        return resultado

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
    objetivo = _norm(modulo)
    with SyncSession() as session:
        mods = session.query(Modulo).all()
        # exacto sin acentos; si no, el nombre del módulo contenido en la consulta
        # (p.ej. "modulo de nomina" -> "Nómina"). No al revés, para no matchear parciales.
        mod = next((m for m in mods if _norm(m.nombre) == objetivo), None) \
            or next((m for m in mods if _norm(m.nombre) in objetivo), None)
        if not mod:
            return {"error": f"Módulo '{modulo}' no encontrado."}
        oferta = _oferta_activa(session, mod.id)
        if not oferta:
            return {
                "modulo": mod.nombre,
                "precio_anual_cop": mod.precio_mensual_cop,
                "precio_mensual_cop": mod.precio_mensual_cop,
                "periodo": "anual",
                "soporte": "incluye soporte técnico por un año",
                "moneda": "COP"
            }
        precio_final = round(mod.precio_mensual_cop * (1 - oferta.descuento_pct / 100))
        return {
            "modulo": mod.nombre,
            "precio_anual_cop": precio_final,
            "precio_mensual_cop": precio_final,
            "precio_regular_cop": mod.precio_mensual_cop,
            "descuento_pct": oferta.descuento_pct,
            "periodo": "anual",
            "soporte": "incluye soporte técnico por un año",
            "moneda": "COP",
        }


def consultar_combos() -> list[dict]:
    """Consulta la lista de combos y paquetes de módulos con sus precios especiales anuales."""
    with SyncSession() as session:
        combos = session.query(Combo).all()
        return [
            {
                "nombre": c.nombre,
                "descripcion": c.descripcion,
                "modulos": c.modulos,
                "precio_anual_cop": c.precio_anual_cop,
                "moneda": "COP",
                "periodo": "anual",
                "soporte": "incluye soporte técnico por un año"
            }
            for c in combos
        ]


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


def _sync_lead_crm(telefono: str, interes: str = "") -> dict:
    """Empuja al CRM el Lead con TODOS los datos del registro local (contacto+cliente),
    fuente de verdad. Upsert por teléfono, así enriquece el mismo lead sin duplicar."""
    with SyncSession() as session:
        contacto = session.get(Contacto, telefono)
        cliente = session.get(Cliente, telefono)
    if not contacto:
        return {"estado": "error", "mensaje": f"No hay contacto registrado con {telefono}."}
    empresa = (cliente.nombre_empresa if cliente else None) or ""
    try:
        lead = espocrm.crear_lead(
            nombre=contacto.nombre, telefono=telefono, empresa=empresa,
            correo=contacto.correo or "", interes=interes, ciudad=contacto.ciudad,
            sector=cliente.sector_empresa if cliente else None,
            actividad=cliente.actividad_empresa if cliente else None,
            empleados=cliente.empleados_empresa if cliente else None,
            identificacion=cliente.numero_identificacion if cliente else None,
            nit=cliente.nit_empresa if cliente else None,
        )
        return {"lead_id": lead.get("id"), "estado": "registrado"}
    except httpx.HTTPError as e:
        return {"estado": "error", "mensaje": f"CRM no disponible: {e}"}


def registrar_lead_crm(
    nombre: str,
    telefono: str,
    empresa: str,
    interes: str,
    sector: str | None = None,
    actividad: str | None = None,
    empleados: str | None = None,
) -> dict:
    with SyncSession() as session:
        _upsert_contacto(session, telefono, nombre)
        _upsert_cliente(
            session, telefono, tipo="lead",
            nombre_empresa=empresa, sector_empresa=sector,
            actividad_empresa=actividad, empleados_empresa=empleados,
        )
        session.commit()
    return _sync_lead_crm(telefono, interes)


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


def _upsert_cliente(session, telefono: str, tipo: str, **campos) -> Cliente | dict:
    """Crea/actualiza la fila de clientes (lead o cliente) para un contacto ya existente.
    Solo pisa campos no-None; nunca degrada tipo de 'cliente' a 'lead'."""
    contacto = session.get(Contacto, telefono)
    if not contacto:
        return {"error": f"No hay contacto registrado con el teléfono {telefono}."}
    cliente = session.get(Cliente, telefono)
    if not cliente:
        cliente = Cliente(telefono=telefono, tipo=tipo)
        session.add(cliente)
    elif cliente.tipo != "cliente":
        cliente.tipo = tipo
    for campo, valor in campos.items():
        if valor is not None:
            setattr(cliente, campo, valor)
    return cliente


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
        if correo is not None:
            contacto.correo = correo
        if ciudad is not None:
            contacto.ciudad = ciudad
        if empresa is not None:
            # empresa es dato de cliente/lead, no de contacto -> clientes.nombre_empresa
            _upsert_cliente(session, telefono, tipo="lead", nombre_empresa=empresa)
        session.commit()
        return {"telefono": telefono, "estado": "guardado"}


def _obtener_horario_atencion() -> str:
    from .db import SyncSession, Parametro
    try:
        with SyncSession() as session:
            param = session.query(Parametro).filter(Parametro.clave == "horario_atencion").first()
            if param and param.valor:
                return param.valor
    except Exception as e:
        logger.error(f"Error al obtener horario_atencion de DB: {e}")
    return "Lunes a Viernes de 8am a 6pm"


def _get_parametro(clave: str) -> str | None:
    """Lee un valor de la tabla parametros; None si no existe o está vacío."""
    try:
        with SyncSession() as session:
            param = session.query(Parametro).filter(Parametro.clave == clave).first()
            if param and param.valor:
                return param.valor
    except Exception as e:
        logger.error("Error al obtener parametro '%s' de DB: %s", clave, e)
    return None


def _alertar_infra_fallo_google(e: Exception, area: str, telefono: str | None = None, nombre: str | None = None):
    """Solo alerta a infra de un fallo de Google (log + correo + WhatsApp al líder de
    infra), SIN escalar el caso del cliente a humano. Se usa en el camino degradado:
    cuando el Calendar no responde el agendamiento sigue con la franja de BD, pero
    infra igual se entera para arreglar el Calendar."""
    logger.exception("Fallo de Google detectado (área=%s): %s", area, e)

    # 1. Enviar correo a infra
    email_infra = os.getenv("EMAIL_INFRA")
    if email_infra:
        try:
            enviar_email(
                email_infra,
                "ALERTA: Fallo en servicios de Google en SysBot",
                f"El bot de WhatsApp detectó un fallo en las APIs de Google.\n\n"
                f"Detalle del error:\n{e}\n\n"
                f"Área afectada: {area}\n"
                f"Contacto: {nombre} ({telefono})"
            )
        except Exception as mail_err:
            logger.error("No se pudo enviar correo de alerta a infra (%s): %s", email_infra, mail_err)

    # 2. Enviar WhatsApp al líder de infra (HU-058)
    whatsapp_lider_infra = _get_parametro("whatsapp_lider_infra")
    if whatsapp_lider_infra:
        try:
            _enviar_whatsapp_directo(
                whatsapp_lider_infra,
                f"ALERTA SysBot: fallo en servicios de Google.\n"
                f"Área: {area}\nContacto: {nombre} ({telefono})\nError: {e}",
            )
        except Exception as wa_err:
            logger.error("No se pudo enviar WhatsApp de alerta al líder de infra (%s): %s", whatsapp_lider_infra, wa_err)
    else:
        logger.info("No hay whatsapp_lider_infra configurado; se omite alerta por WhatsApp a infra.")


def _manejar_fallo_google(e: Exception, area: str, telefono: str | None = None, nombre: str | None = None, resumen: str | None = None):
    """Fallo de Google que además requiere escalar el caso del cliente a humano:
    alerta a infra (log + correo + WhatsApp) y luego escala. Se usa cuando el fallo
    deja al cliente sin atención posible; el camino degradado usa solo
    _alertar_infra_fallo_google."""
    _alertar_infra_fallo_google(e, area, telefono, nombre)
    if telefono and nombre:
        try:
            escalar_a_humano(
                telefono=telefono,
                nombre=nombre,
                resumen_caso=resumen or f"Fallo en servicio de Google. Motivo: {e}",
                area=area
            )
        except Exception as esc_err:
            logger.error("Fallo al auto-escalar por fallo de Google: %s", esc_err)


def agendar_cita(nombre: str, telefono: str, motivo: str, fecha: str, hora: str, area: str) -> dict:
    """Agenda una cita si el horario pedido está libre en el calendario de la primera
    persona disponible de esa área (según su rango horario propio). fecha: 'YYYY-MM-DD'.
    hora: 'HH:MM'.
    area: p.ej. 'comercial' o 'soporte'. Si nadie de esa área está libre, devuelve
    alternativas libres ese mismo día (unión de todas las personas del área)."""
    with SyncSession() as session:
        personas = _agentes_por_area(session, area)
        contacto = session.get(Contacto, telefono)
        correo_cliente = contacto.correo if contacto else None
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
            try:
                libres = horarios_libres(fecha, persona.email, persona.hora_inicio, persona.hora_fin)
            except Exception as e:
                # Degradado: no se pudo consultar el Calendar del agente -> se usa la
                # franja horaria de la BD (hora_inicio/hora_fin) como disponibilidad.
                # Se alerta a infra pero NO se escala ni se bloquea al cliente.
                _alertar_infra_fallo_google(e, area, telefono, nombre)
                logger.warning(
                    "Calendar no disponible para %s (%s); usando franja horaria de BD.",
                    persona.nombre, persona.email
                )
                libres = _franjas_bd(persona.hora_inicio, persona.hora_fin)
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
                    evento = crear_evento_calendar(nombre, telefono, motivo, fecha, hora, persona.email, correo_cliente)
                    cita["calendar_link"] = evento.get("htmlLink")
                except Exception as e:
                    # Degradado: la cita ya quedó registrada en _CITAS_DB; no se pudo
                    # crear el evento en Google Calendar. Se alerta a infra y se sigue
                    # (el cliente igual queda agendado con la franja de BD).
                    _alertar_infra_fallo_google(e, area, telefono, nombre)
                    cita["calendar_error"] = str(e)
                    cita["calendar_degradado"] = True
                if correo_cliente:
                    try:
                        enviar_email(
                            correo_cliente,
                            f"Confirmación de cita SysPlus - {fecha} {hora}",
                            f"Hola {nombre},\n\nTu cita quedó registrada:\nMotivo: {motivo}\n"
                            f"Fecha: {fecha}\nHora: {hora}\nTe atenderá: {persona.nombre} ({area}).\n\nSaludos, SysPlus.",
                        )
                        cita["email_enviado"] = True
                    except Exception as e:
                        # Degradado: la cita ya está registrada; el correo de
                        # confirmación falló. Se alerta a infra y se sigue.
                        _alertar_infra_fallo_google(e, area, telefono, nombre)
                        cita["email_enviado"] = False
                        cita["email_error"] = str(e)
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
            try:
                libres.update(horarios_libres(d, persona.email, persona.hora_inicio, persona.hora_fin))
            except Exception as e:
                # Degradado: no se pudo consultar el Calendar del agente -> se usa la
                # franja horaria de la BD como disponibilidad. Se alerta a infra pero
                # NO se escala ni se corta la respuesta al cliente.
                _alertar_infra_fallo_google(e, area)
                logger.warning(
                    "Calendar no disponible para %s (%s); usando franja horaria de BD.",
                    persona.nombre, persona.email
                )
                libres.update(_franjas_bd(persona.hora_inicio, persona.hora_fin))
        resultado.append({"fecha": d, "horarios_libres": sorted(libres)})
    return resultado


def crear_ticket_soporte(telefono: str, descripcion: str, modulo: str) -> dict:
    from .db import Conversacion
    with SyncSession() as session:
        # 1. Obtener o crear area soporte
        area_row = _get_area(session, "soporte")
        
        # 2. Obtener conversación activa para este teléfono
        conv = session.query(Conversacion).filter(
            Conversacion.telefono == telefono,
            Conversacion.estado == "abierta"
        ).order_by(Conversacion.id.desc()).first()
        
        # 3. Crear Radicado
        codigo_rand = f"ESC-{str(uuid.uuid4())[:8].upper()}"
        radicado = Radicado(
            telefono=telefono,
            area_id=area_row.id,
            resumen=f"Soporte {modulo}: {descripcion}",
            estado="escalado",
            codigo=codigo_rand
        )
        session.add(radicado)
        session.flush()
        
        if conv:
            conv.radicado_id = radicado.id
            
        caso_id = radicado.codigo
        
        # 4. Crear caso en EspoCRM
        crm_case_id = None
        crm_case_number = None
        try:
            caso_crm = espocrm.crear_caso(telefono, f"[{caso_id}] {descripcion}", modulo)
            crm_case_id = caso_crm.get("id")
            crm_case_number = caso_crm.get("number")
            radicado.crm_case_id = crm_case_id
        except httpx.HTTPError as e:
            logger.exception("espocrm.crear_caso falló en crear_ticket_soporte para caso_id=%s", caso_id)
            
        session.commit()
        
        if not crm_case_id:
            return {
                "ticket_id": caso_id,
                "crm_case_number": None,
                "estado": "abierto_local",
                "mensaje": "Ticket registrado localmente. Sincronización con CRM pendiente."
            }
            
        return {"ticket_id": caso_id, "crm_case_number": crm_case_number, "estado": "abierto"}


def consultar_ticket_soporte(ticket_id: str) -> dict:
    # Si el ticket_id es puramente numérico (ej: "20" o 20)
    if str(ticket_id).isdigit():
        try:
            caso = espocrm.consultar_caso_por_numero(int(ticket_id))
            if caso:
                return caso
            return {"error": "no encontrado", "mensaje": f"No existe ningún caso con número {ticket_id} en el CRM."}
        except httpx.HTTPError as e:
            return {"error": f"CRM no disponible: {e}"}

    crm_id = ticket_id
    
    # Si parece un código de radicado ESC-XXXX
    if ticket_id.startswith("ESC-"):
        with SyncSession() as session:
            radicado = session.query(Radicado).filter(Radicado.codigo == ticket_id).first()
            if not radicado:
                # Intentar buscar por ID si el código es ESC-<id>
                try:
                    radicado_id = int(ticket_id.removeprefix("ESC-"))
                    radicado = session.get(Radicado, radicado_id)
                except ValueError:
                    pass
            if radicado and radicado.crm_case_id:
                crm_id = radicado.crm_case_id
            else:
                return {"error": "no encontrado", "mensaje": f"No se encontró ningún radicado con código {ticket_id} en la base de datos."}

    try:
        return espocrm.consultar_caso(crm_id)
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


def reclasificar_caso_sin_licencia(caso_id: str, telefono: str, nombre: str) -> dict:
    """Si ya existía un radicado (ESC-<id>) de soporte y luego se detecta que el contacto
    NO tiene licencia activa: comenta y bloquea (Rejected) el caso original en EspoCRM,
    y lo reescala a comercial (nuevo radicado). Llamar apenas consultar_licencia devuelva
    sin_licencia si ya se había creado un ticket/escalamiento antes de esa verificación."""
    with SyncSession() as session:
        radicado = session.query(Radicado).filter(Radicado.codigo == caso_id).first()
        if not radicado:
            try:
                radicado_id = int(caso_id.removeprefix("ESC-"))
                radicado = session.get(Radicado, radicado_id)
            except ValueError:
                pass

        if not radicado:
            return {"estado": "error", "mensaje": f"No existe el radicado {caso_id}."}

        comentario = f"Sin licencia activa para {nombre} ({telefono}); redirigido a comercial."
        if radicado.crm_case_id:
            try:
                espocrm.comentar_caso(radicado.crm_case_id, comentario)
                espocrm.actualizar_estado_caso(radicado.crm_case_id, "Rejected")
            except httpx.HTTPError:
                logger.exception("No se pudo comentar/bloquear caso CRM %s", radicado.crm_case_id)

        radicado.estado = "bloqueado_sin_licencia"
        session.commit()

    return escalar_a_humano(telefono, nombre, f"Redirigido desde {caso_id}: sin licencia activa.", "comercial")


def escalar_a_humano(telefono: str, nombre: str, resumen_caso: str, area: str) -> dict:
    """Escala la conversación a un agente humano del área dada. Busca el primer agente
    del área que NO esté ya conectado con otro cliente. Si es de opción B (mismo
    WhatsApp del bot), lo conecta y el bot se pausa para este cliente. Si es de
    opción A, le notifica el caso por WhatsApp aparte (no se pausa). Si todos los
    agentes del área están ocupados, encola al cliente e informa su posición.
    Siempre registra el caso por correo a EMAIL_SOPORTE y deja radicado persistido
    (tabla radicados) y traza en EspoCRM."""
    with SyncSession() as session:
        _upsert_contacto(session, telefono, nombre)
        area_row = _get_area(session, area)
        
        from .db import Conversacion
        conv = session.query(Conversacion).filter(
            Conversacion.telefono == telefono,
            Conversacion.estado == "abierta"
        ).order_by(Conversacion.id.desc()).first()

        import uuid
        if conv and conv.radicado_id:
            radicado = session.query(Radicado).get(conv.radicado_id)
            radicado.resumen = resumen_caso
            radicado.area_id = area_row.id
            radicado.estado = "escalado"
            if not radicado.codigo:
                radicado.codigo = f"ESC-{str(uuid.uuid4())[:8].upper()}"
            session.flush()
            caso_id = radicado.codigo
        else:
            codigo_rand = f"ESC-{str(uuid.uuid4())[:8].upper()}"
            radicado = Radicado(
                telefono=telefono, area_id=area_row.id, resumen=resumen_caso, estado="escalado",
                codigo=codigo_rand
            )
            session.add(radicado)
            session.flush()
            if conv:
                conv.radicado_id = radicado.id
            caso_id = radicado.codigo

        try:
            crm_case = espocrm.crear_caso(telefono, f"[{caso_id}] {resumen_caso}", area)
            radicado.crm_case_id = crm_case.get("id")
        except httpx.HTTPError:
            logger.exception("espocrm.crear_caso falló para caso_id=%s", caso_id)

        cuerpo = f"Cliente: {nombre}\nTeléfono: {telefono}\nResumen: {resumen_caso}"
        try:
            enviar_email(EMAIL_SOPOPRTE if False else EMAIL_SOPORTE, f"[{caso_id}] Escalamiento SysBot - {nombre}", cuerpo)
            radicado.email_enviado = True
        except Exception as e:
            logger.exception("enviar_email falló en escalar_a_humano para caso_id=%s: %s", caso_id, e)
            radicado.email_enviado = False

        agentes = _agentes_por_area(session, area)
        numero_bot = session.query(Parametro).filter(Parametro.clave == "whatsapp_numero_bot").first()
        if not agentes:
            session.commit()
            return {
                "caso_id": caso_id, "estado": "escalado", "modo": None, "atendido_por": None,
                "email_enviado": radicado.email_enviado,
                "mensaje": f"Caso {caso_id} registrado, pero no hay agentes configurados para el área '{area}'.",
            }

        ocupados = _ocupados()
        libres = [a for a in agentes if a.id not in ocupados]
        if libres:
            agente = libres[0]
            radicado.agente_id = agente.id
            if agente.telefono and numero_bot and agente.telefono == numero_bot.valor:
                modo = "conectado"
                contacto = _upsert_contacto(session, telefono, nombre)
                contacto.atendido_por = agente.id
                contacto.conectado_en = datetime.now(timezone.utc)
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
            radicado.modo = modo
            session.commit()
            return {
                "caso_id": caso_id, "estado": "escalado", "modo": modo, "atendido_por": agente.nombre,
                "email_enviado": radicado.email_enviado,
                "mensaje": mensaje,
            }

        # todos ocupados -> cola
        radicado.estado = "en_cola"
        delante = (
            session.query(Conversacion)
            .join(Radicado, Conversacion.radicado_id == Radicado.id)
            .filter(
                Radicado.area_id == area_row.id,
                Conversacion.espera_desde.isnot(None),
                Conversacion.espera_hasta.is_(None),
                Conversacion.id != (conv.id if conv else -1),
            )
            .count()
        )
        if conv:
            conv.espera_desde = datetime.now(timezone.utc)
            conv.espera_hasta = None
        session.commit()

        # HU-059: notificar al líder comercial del área que un caso quedó en cola
        # (solo aquí, nunca en la rama de asignación directa a agente libre).
        whatsapp_lider_area = _get_parametro(f"whatsapp_lider_{_norm(area)}")
        if whatsapp_lider_area:
            try:
                _enviar_whatsapp_directo(
                    whatsapp_lider_area,
                    f"[{caso_id}] Caso de {nombre} en cola (área {area}), posición {delante + 1}.",
                )
            except Exception as wa_err:
                logger.error("No se pudo notificar por WhatsApp al líder de %s (%s): %s", area, whatsapp_lider_area, wa_err)
        else:
            logger.info("No hay whatsapp_lider_%s configurado; se omite alerta de cola.", _norm(area))

        return {
            "caso_id": caso_id, "estado": "en_cola", "posicion": delante + 1,
            "email_enviado": radicado.email_enviado,
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
        from .db import Conversacion
        numero_bot = session.query(Parametro).filter(Parametro.clave == "whatsapp_numero_bot").first()
        ocupados = _ocupados()
        areas = (
            session.query(Area)
            .join(Radicado, Radicado.area_id == Area.id)
            .join(Conversacion, Conversacion.radicado_id == Radicado.id)
            .filter(
                Conversacion.espera_desde.isnot(None),
                Conversacion.espera_hasta.is_(None)
            )
            .distinct()
            .all()
        )
        for area_row in areas:
            libres = [
                a for a in _agentes_por_area(session, area_row.nombre)
                if a.id not in ocupados and a.telefono and numero_bot and a.telefono == numero_bot.valor
            ]
            cola = (
                session.query(Conversacion)
                .join(Radicado, Conversacion.radicado_id == Radicado.id)
                .filter(
                    Radicado.area_id == area_row.id,
                    Conversacion.espera_desde.isnot(None),
                    Conversacion.espera_hasta.is_(None)
                )
                .order_by(Conversacion.espera_desde)
                .all()
            )
            for agente, conv_espera in zip(libres, cola):
                contacto = session.get(Contacto, conv_espera.telefono)
                contacto.atendido_por = agente.id
                contacto.conectado_en = datetime.now(timezone.utc)
                ocupados.add(agente.id)
                
                conv_espera.espera_hasta = datetime.now(timezone.utc)
                
                radicado = session.get(Radicado, conv_espera.radicado_id)
                if radicado:
                    radicado.agente_id = agente.id
                    radicado.estado = "escalado"
                    radicado.modo = "conectado"
                    
                promovidos.append({
                    "telefono": conv_espera.telefono,
                    "mensaje": f"¡Ya te toca {contacto.nombre}! {agente.nombre} te va a atender ahora, un momento.",
                })
        session.commit()
    return promovidos


def registrar_cliente(
    telefono: str,
    numero_identificacion: str | None = None,
    nit_empresa: str | None = None,
    nombre_empresa: str | None = None,
    sector: str | None = None,
    actividad: str | None = None,
    empleados: str | None = None,
) -> dict:
    """Marca un contacto existente como cliente confirmado, guardando su identificación
    (y la de su empresa, si aplica). Requiere que el contacto ya exista (se crea al
    escalar o al registrar_lead_crm)."""
    with SyncSession() as session:
        cliente = _upsert_cliente(
            session, telefono, tipo="cliente",
            numero_identificacion=numero_identificacion, nit_empresa=nit_empresa,
            nombre_empresa=nombre_empresa, sector_empresa=sector,
            actividad_empresa=actividad, empleados_empresa=empleados,
        )
        if isinstance(cliente, dict):
            return cliente
        session.commit()
    # GAP 3: cédula/NIT/perfil también deben viajar al CRM, no solo a la BD local.
    _sync_lead_crm(telefono)
    return {"telefono": telefono, "estado": "cliente_registrado"}


def finalizar_conversacion(telefono: str, motivo_cierre: str = "usuario") -> dict:
    """Cierra la conversación actual de forma explícita.
    Debe llamarse cuando el usuario se despide o indica que ya no requiere más ayuda."""
    with SyncSession() as session:
        from .db import Conversacion
        conv = session.query(Conversacion).filter(
            Conversacion.telefono == telefono,
            Conversacion.estado == "abierta"
        ).order_by(Conversacion.id.desc()).first()
        
        if conv:
            conv.estado = "cerrada"
            conv.motivo_cierre = motivo_cierre
            if conv.espera_desde and not conv.espera_hasta:
                conv.espera_hasta = datetime.now(timezone.utc)
            session.commit()
            return {"status": "cerrada", "motivo": motivo_cierre}
        return {"status": "error", "mensaje": "No hay conversación abierta para cerrar."}


# Dynamic decoration for Prometheus instrumentation
from functools import wraps
from .prometheus_metrics import demobot_tool_calls_total

def _instrument_tool(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            res = func(*args, **kwargs)
            demobot_tool_calls_total.labels(tool_name=func.__name__, status="success").inc()
            return res
        except Exception as e:
            demobot_tool_calls_total.labels(tool_name=func.__name__, status="failure").inc()
            raise e
    return wrapper

# Decorate public tool functions
buscar_en_knowledge = _instrument_tool(buscar_en_knowledge)
consultar_precio_modulo = _instrument_tool(consultar_precio_modulo)
consultar_combos = _instrument_tool(consultar_combos)
consultar_disponibilidad_agenda = _instrument_tool(consultar_disponibilidad_agenda)
consultar_ticket_soporte = _instrument_tool(consultar_ticket_soporte)
consultar_licencia = _instrument_tool(consultar_licencia)
crear_tarea = _instrument_tool(crear_tarea)
consultar_ofertas_activas = _instrument_tool(consultar_ofertas_activas)
consultar_parametro = _instrument_tool(consultar_parametro)
registrar_lead_crm = _instrument_tool(registrar_lead_crm)
consultar_estado_cliente = _instrument_tool(consultar_estado_cliente)
guardar_datos_contacto = _instrument_tool(guardar_datos_contacto)
agendar_cita = _instrument_tool(agendar_cita)
crear_ticket_soporte = _instrument_tool(crear_ticket_soporte)
escalar_a_humano = _instrument_tool(escalar_a_humano)
registrar_cliente = _instrument_tool(registrar_cliente)
finalizar_conversacion = _instrument_tool(finalizar_conversacion)

