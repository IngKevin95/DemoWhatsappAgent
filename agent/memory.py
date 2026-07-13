from datetime import datetime, timedelta

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from .db import Base, async_engine

engine = async_engine
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Mensaje(Base):
    """Log inmutable de chat (sin Auditoria — timestamp ya cumple ese rol, nunca se actualiza).
    area_id: área a la que pertenecía el contacto al momento del mensaje (NULL si aún
    no escalado). Útil para reportes por área sin depender del estado actual del contacto."""
    __tablename__ = "mensajes"

    id = Column(Integer, primary_key=True)
    telefono = Column(String, ForeignKey("contactos.telefono"), index=True)
    role = Column(String)
    content = Column(String)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


async def inicializar_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def guardar_mensaje(telefono: str, role: str, content: str, area_id: int | None = None):
    async with SessionLocal() as session:
        session.add(Mensaje(telefono=telefono, role=role, content=content, area_id=area_id))
        await session.commit()


async def obtener_historial(telefono: str, limite: int = 20) -> list[dict]:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Mensaje)
            .where(Mensaje.telefono == telefono)
            .order_by(Mensaje.timestamp.desc())
            .limit(limite)
        )
        mensajes = result.scalars().all()
        mensajes.reverse()
        return [{"role": m.role, "content": m.content} for m in mensajes]


async def ultimo_timestamp(telefono: str) -> datetime | None:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Mensaje.timestamp)
            .where(Mensaje.telefono == telefono)
            .order_by(Mensaje.timestamp.desc())
            .limit(1)
        )
        row = result.first()
        return row[0] if row else None


async def ultimo_mensaje(telefono: str) -> dict | None:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Mensaje)
            .where(Mensaje.telefono == telefono)
            .order_by(Mensaje.timestamp.desc())
            .limit(1)
        )
        m = result.scalars().first()
        if not m:
            return None
        return {"role": m.role, "content": m.content, "timestamp": m.timestamp}


async def telefonos_con_actividad_reciente(horas: int = 24) -> list[str]:
    async with SessionLocal() as session:
        desde = datetime.utcnow() - timedelta(hours=horas)
        result = await session.execute(
            select(Mensaje.telefono).where(Mensaje.timestamp >= desde).distinct()
        )
        return [row[0] for row in result.all()]


async def limpiar_historial(telefono: str):
    async with SessionLocal() as session:
        result = await session.execute(select(Mensaje).where(Mensaje.telefono == telefono))
        for m in result.scalars().all():
            await session.delete(m)
        await session.commit()
