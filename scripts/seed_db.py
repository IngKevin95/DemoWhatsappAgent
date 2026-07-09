"""Crea tablas (si faltan) y siembra módulos base. Idempotente: no duplica si ya hay datos."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.db import Agente, Area, Base, Modulo, Parametro, SyncSession, sync_engine

# placeholder: reemplazar email/telefono reales por persona vía NocoDB, y compartir
# su calendario (ver/free-busy) con la cuenta de Google usada por el bot. Si
# telefono == parametro whatsapp_numero_bot, el escalamiento es opción B (mismo
# hilo); si no, opción A (notificación a otro WhatsApp).
AGENTES = [
    {"area": "comercial", "nombre": "Comercial 1", "email": "comercial1@sysplus.com", "telefono": None, "hora_inicio": "09:00", "hora_fin": "18:00"},
    {"area": "soporte", "nombre": "Soporte 1", "email": "soporte1@sysplus.com", "telefono": None, "hora_inicio": "08:00", "hora_fin": "17:00"},
]

PRECIOS_MODULOS = {
    "Productos": 350000, "Inventario": 450000, "Facturación": 500000,
    "Cartera": 400000, "Compras": 400000, "Cuentas por pagar": 350000,
    "Tesorería": 380000, "Importaciones": 600000, "CRM": 450000,
    "Producción": 700000, "Nómina": 550000, "Contabilidad": 500000, "POS": 450000,
}

PARAMETROS = {
    "horario_atencion": ("Lunes a viernes, 8:00 am - 6:00 pm", "Horario de atención comercial y soporte"),
    "email_soporte": (os.getenv("EMAIL_SOPORTE", "soporte@sysplus.com"), "Correo de escalamiento a soporte humano"),
    "whatsapp_numero_bot": (os.getenv("META_PHONE_NUMBER_ID", ""), "Número/ID de WhatsApp del bot (para detectar escalamiento opción B)"),
    "correo_comercial": ("comercial@sysplus.com", "Correo general del área comercial"),
    "correo_info": ("info@sysplus.com", "Correo general de información"),
    "correo_soporte": ("soporte@sysplus.com", "Correo general de soporte"),
    "correo_proveedores": ("proveedores@sysplus.com", "Correo general para proveedores"),
    "timeout_pausa_minutos": ("60", "Minutos de inactividad tras los cuales una pausa (opción B) se cierra sola"),
}

if __name__ == "__main__":
    Base.metadata.create_all(sync_engine)
    with SyncSession() as session:
        if session.query(Modulo).count() == 0:
            session.add_all(
                Modulo(nombre=nombre, precio_mensual_cop=precio)
                for nombre, precio in PRECIOS_MODULOS.items()
            )
            session.commit()
            print(f"Sembrados {len(PRECIOS_MODULOS)} módulos.")
        else:
            print("Tabla modulos ya tiene datos, no se siembra.")

        if session.query(Parametro).count() == 0:
            session.add_all(
                Parametro(clave=clave, valor=valor, descripcion=desc)
                for clave, (valor, desc) in PARAMETROS.items()
            )
            session.commit()
            print(f"Sembrados {len(PARAMETROS)} parámetros.")
        else:
            print("Tabla parametros ya tiene datos, no se siembra.")

        if session.query(Agente).count() == 0:
            nombres_area = {a["area"] for a in AGENTES}
            areas_existentes = {a.nombre: a for a in session.query(Area).filter(Area.nombre.in_(nombres_area)).all()}
            for nombre in nombres_area - areas_existentes.keys():
                area = Area(nombre=nombre)
                session.add(area)
                session.flush()
                areas_existentes[nombre] = area
            session.add_all(
                Agente(**{k: v for k, v in a.items() if k != "area"}, area_id=areas_existentes[a["area"]].id)
                for a in AGENTES
            )
            session.commit()
            print(f"Sembrados {len(AGENTES)} agentes (editar email/telefono reales en NocoDB).")
        else:
            print("Tabla agentes ya tiene datos, no se siembra.")
