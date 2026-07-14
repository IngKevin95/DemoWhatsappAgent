import os
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Computed, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://sysbot:sysbot@localhost:5432/sysbot")
SYNC_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
ASYNC_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

sync_engine = create_engine(SYNC_URL, echo=False)
SyncSession = sessionmaker(sync_engine)

async_engine = create_async_engine(ASYNC_URL, echo=False)


class Base(DeclarativeBase):
    pass


class Auditoria:
    """Mixin: creado_en/actualizado_en, mantenidos infaliblemente por trigger de Postgres
    (ver migración) para que también cubran escrituras directas desde NocoDB."""
    # naive UTC: las columnas son TIMESTAMP WITHOUT TIME ZONE. asyncpg rechaza
    # datetimes tz-aware contra esas columnas (psycopg2 los toleraba en silencio).
    creado_en = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    actualizado_en = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class Modulo(Auditoria, Base):
    __tablename__ = "modulos"

    id = Column(Integer, primary_key=True)
    nombre = Column(String, unique=True, nullable=False)
    precio_mensual_cop = Column(Integer, nullable=False)


class Oferta(Auditoria, Base):
    __tablename__ = "ofertas"

    id = Column(Integer, primary_key=True)
    modulo_id = Column(Integer, ForeignKey("modulos.id"), nullable=False)
    descuento_pct = Column(Integer, nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    activo = Column(Boolean, default=True)


class Parametro(Auditoria, Base):
    __tablename__ = "parametros"

    clave = Column(String, primary_key=True)
    valor = Column(String, nullable=False)
    descripcion = Column(String)


class Area(Auditoria, Base):
    """Catálogo de áreas (comercial, soporte, ...). Maestro compartido: Agente y
    ColaEspera apuntan aquí por FK en vez de repetir el nombre como string suelto."""
    __tablename__ = "areas"

    id = Column(Integer, primary_key=True)
    nombre = Column(String, unique=True, nullable=False)


class Agente(Auditoria, Base):
    """Personas a las que se puede escalar comunicación/citas, agrupadas por área.
    Cada fila = una persona con su propio calendario (email), teléfono y rango horario.
    Si telefono == parametro whatsapp_numero_bot, el escalamiento es opción B
    (la persona responde dentro del mismo hilo de WhatsApp del bot); si no, opción A
    (se le notifica el caso a su propio número). Libre/ocupado se deriva de
    Contacto.atendido_por (sin duplicar el estado acá)."""
    __tablename__ = "agentes"

    id = Column(Integer, primary_key=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False)
    nombre = Column(String, nullable=False)
    email = Column(String, nullable=False)  # también Calendar ID (debe estar compartido con la cuenta de servicio)
    telefono = Column(String, nullable=True)  # WhatsApp del agente; ver docstring
    hora_inicio = Column(String, nullable=False, default="09:00")
    hora_fin = Column(String, nullable=False, default="18:00")
    activo = Column(Boolean, default=True)


class Contacto(Auditoria, Base):
    """Cualquier persona que escribe al bot. Datos básicos + a qué agente está
    conectada ahora mismo (opción B). Se libera manualmente (endpoint
    POST /agentes/{telefono}/liberar, o vaciando atendido_por desde NocoDB)
    o por timeout mutuo (parámetro timeout_pausa_minutos)."""
    __tablename__ = "contactos"

    telefono = Column(String, primary_key=True)
    nombre = Column(String, nullable=False)
    empresa = Column(String, nullable=True)
    correo = Column(String, nullable=True)
    ciudad = Column(String, nullable=True)
    atendido_por = Column(Integer, ForeignKey("agentes.id"), nullable=True)
    conectado_en = Column(DateTime, nullable=True)
    consentimiento_datos = Column(Boolean, default=False)
    canal = Column(String, nullable=False, default="meta")


class Cliente(Auditoria, Base):
    """Extiende Contacto solo para quienes son clientes (no todo contacto lo es)."""
    __tablename__ = "clientes"

    telefono = Column(String, ForeignKey("contactos.telefono"), primary_key=True)
    numero_identificacion = Column(String, nullable=True)  # cédula/NIT de la persona
    nit_empresa = Column(String, nullable=True)  # solo si además tiene empresa
    tipo = Column(String, nullable=False, default="lead")  # 'lead' o 'cliente'
    nombre_empresa = Column(String, nullable=True)
    sector_empresa = Column(String, nullable=True)
    actividad_empresa = Column(String, nullable=True)  # a qué se dedica
    empleados_empresa = Column(String, nullable=True)  # texto libre: "10-50", "aprox 20"


class Radicado(Auditoria, Base):
    """Registro persistente de cada escalamiento a humano (radicado ESC-<id>).
    El id lo asigna el serial de Postgres: es la fuente única del número de
    radicado, así que no puede colisionar ni duplicarse entre escalamientos
    concurrentes (a diferencia de un random.randint generado en la app)."""
    __tablename__ = "radicados"

    id = Column(Integer, primary_key=True)
    telefono = Column(String, ForeignKey("contactos.telefono"), nullable=False)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False)
    agente_id = Column(Integer, ForeignKey("agentes.id"), nullable=True)
    resumen = Column(String, nullable=False)
    estado = Column(String, nullable=False)  # escalado | en_cola
    modo = Column(String, nullable=True)  # conectado | notificacion_con_contacto | notificacion
    email_enviado = Column(Boolean, default=False)
    crm_case_id = Column(String, nullable=True)


class Conversacion(Auditoria, Base):
    """Agrupa mensajes de un mismo contacto. Si se escala, se liga a un Radicado."""
    __tablename__ = "conversaciones"

    id = Column(Integer, primary_key=True)
    telefono = Column(String, ForeignKey("contactos.telefono"), nullable=False)
    radicado_id = Column(Integer, ForeignKey("radicados.id"), nullable=True)
    estado = Column(String, nullable=False, default="abierta")  # abierta | cerrada
    tipo_solicitud = Column(String, nullable=True)
    motivo_cierre = Column(String, nullable=True)  # usuario | inactividad


class ColaEspera(Auditoria, Base):
    """Contactos esperando a que se libere un agente de su área (todos ocupados).
    telefono es PK+FK a Contacto: la relación misma es la clave.
    area_id es FK a Area: el área solicitada (agente_id aún NULL mientras espera).
    agente_id: quién terminó atendiendo (se llena al promover, trazabilidad).
    desde/hasta: inicio/fin de espera (hasta NULL = sigue en cola).
    duracion_seg: calculada por Postgres (GENERATED), no por la app."""
    __tablename__ = "cola_espera"

    telefono = Column(String, ForeignKey("contactos.telefono"), primary_key=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False)
    agente_id = Column(Integer, ForeignKey("agentes.id"), nullable=True)
    desde = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    hasta = Column(DateTime, nullable=True)
    duracion_seg = Column(
        Integer,
        Computed("EXTRACT(EPOCH FROM (hasta - desde))::int", persisted=True),
    )
