"""Seeds the database with 30 days of realistic, randomized synthetic data for contacts, clients, radicados, and conversations."""
import os
import sys
import random
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.db import Base, Contacto, Cliente, Radicado, Conversacion, Area, Agente, Oferta, Modulo, SyncSession, sync_engine
from agent.memory import Mensaje

def delete_old_synthetic_data(session):
    """Deletes existing conversations, radicados, clients, and contacts to prevent duplicates/conflicts."""
    print("Clearing old transactional data...")
    session.query(Mensaje).delete()
    session.query(Conversacion).delete()
    session.query(Radicado).delete()
    session.query(Cliente).delete()
    # Delete contacts that are not linked to agents
    session.query(Contacto).delete()
    session.commit()

def generate_phone():
    return f"+573{random.randint(100000000, 999999999)}"

def seed():
    Base.metadata.create_all(sync_engine)
    session = SyncSession()

    # Garantiza la columna resuelto_en en DBs ya existentes (create_all no altera tablas).
    from sqlalchemy import text
    session.execute(text("ALTER TABLE radicados ADD COLUMN IF NOT EXISTS resuelto_en timestamp without time zone"))
    session.commit()

    delete_old_synthetic_data(session)

    # Get areas and agents
    areas = session.query(Area).all()
    if not areas:
        print("Error: No areas found. Run seed_db.py first.")
        return

    # Garantiza un equipo realista: varios comerciales y soportes. Respeta los
    # agentes maestros ya existentes (seed_db) y solo agrega los que falten.
    area_por_nombre = {a.nombre: a for a in areas}
    equipo = {
        "comercial": ["Laura Ríos", "Andrés Peña", "Camila Torres", "Julián Mora"],
        "soporte": ["Diego Salas", "Paola Ortiz", "Mateo Vega", "Natalia Cruz", "Óscar Lema"],
    }
    for area_nombre, nombres in equipo.items():
        area = area_por_nombre.get(area_nombre)
        if not area:
            continue
        existentes = {a.nombre for a in session.query(Agente).filter(Agente.area_id == area.id).all()}
        for nombre in nombres:
            if nombre in existentes:
                continue
            session.add(Agente(
                area_id=area.id, nombre=nombre,
                email=f"{nombre.lower().replace(' ', '.').replace('í','i').replace('ó','o')}@democorp.com",
                telefono=None,
                hora_inicio=random.choice(["07:00", "08:00", "09:00"]),
                hora_fin=random.choice(["16:00", "17:00", "18:00"]),
                activo=random.choice([True, True, True, False]),  # ~75% activos
            ))
    session.commit()

    agents = session.query(Agente).all()
    if not agents:
        print("Error: No agents found. Run seed_db.py first.")
        return

    # Ofertas de catálogo: algunas vigentes hoy, otras pasadas/futuras (realista).
    session.query(Oferta).delete()
    modulos = session.query(Modulo).all()
    if modulos:
        hoy = datetime.utcnow().date()
        ofertas_cfg = [
            (random.choice(modulos), 15, hoy - timedelta(days=5), hoy + timedelta(days=10), True),   # vigente
            (random.choice(modulos), 20, hoy - timedelta(days=2), hoy + timedelta(days=20), True),   # vigente
            (random.choice(modulos), 10, hoy + timedelta(days=7), hoy + timedelta(days=30), True),    # futura
            (random.choice(modulos), 25, hoy - timedelta(days=40), hoy - timedelta(days=10), False),  # vencida
        ]
        for mod, pct, ini, fin, act in ofertas_cfg:
            session.add(Oferta(modulo_id=mod.id, descuento_pct=pct, fecha_inicio=ini, fecha_fin=fin, activo=act))
        session.commit()

    area_dict = {a.nombre: a.id for a in areas}
    agents_by_area = {}
    for agent in agents:
        agents_by_area.setdefault(agent.area_id, []).append(agent)

    cities = ["Bogotá", "Medellín", "Cali", "Barranquilla", "Bucaramanga", "Cartagena", "Manizales", "Pereira"]
    first_names = ["Juan", "María", "Carlos", "Ana", "Luis", "Diana", "Andrés", "Laura", "Pedro", "Sandra"]
    last_names = ["Gómez", "Rodríguez", "González", "Martínez", "López", "Pérez", "Sánchez", "Ramírez"]
    sectors = ["Tecnología", "Comercio", "Servicios", "Manufactura", "Salud", "Educación"]
    activities = ["Venta al por menor", "Desarrollo de software", "Consultoría", "Distribución", "Servicios médicos"]
    employee_ranges = ["1-10", "11-50", "51-200", "200+"]
    user_msgs = [
        "Hola, quiero información de precios", "¿Tienen licencia para el módulo de facturación?",
        "Necesito soporte, el sistema no carga", "¿Qué combos manejan?", "Gracias, muy amable",
        "¿Cómo renuevo mi licencia?", "Tengo un error al generar el reporte", "Quiero agendar una demo",
    ]
    bot_msgs = [
        "Con gusto, te comparto la información", "Claro, el módulo tiene un valor mensual",
        "Entiendo, déjame escalar tu caso a soporte", "Tenemos varios combos disponibles",
        "¡A la orden! Quedo atento", "Te ayudo con la renovación", "Voy a revisar ese error",
    ]

    now = datetime.utcnow()
    DAYS = 180  # ~6 meses de historia para que los tableros tengan tendencia
    start_date = now - timedelta(days=DAYS)

    total_conversations = 0
    total_contacts = 0
    total_clients = 0
    total_radicados = 0
    total_messages = 0

    print(f"Generating {DAYS} days of synthetic data...")

    # Iterate over the last DAYS days
    for day in range(DAYS + 1):
        current_day = start_date + timedelta(days=day)
        # Random number of conversations per day (5 to 15)
        num_convs = random.randint(8, 20)
        
        for _ in range(num_convs):
            # Generate random hour for the conversation
            conv_time = current_day.replace(
                hour=random.randint(8, 20),
                minute=random.randint(0, 59),
                second=random.randint(0, 59),
                microsecond=0
            )

            # Avoid generating future timestamps
            if conv_time > now:
                continue

            # Create Contact
            phone = generate_phone()
            name = f"{random.choice(first_names)} {random.choice(last_names)}"
            email = f"{name.lower().replace(' ', '.')}@example.com"
            city = random.choice(cities)
            
            contacto = Contacto(
                telefono=phone,
                nombre=name,
                correo=email,
                ciudad=city,
                consentimiento_datos=random.choice([True, True, False]),
                canal=random.choice(["meta", "meta", "telegram"]),
                creado_en=conv_time,
                actualizado_en=conv_time
            )
            session.add(contacto)
            session.flush()
            total_contacts += 1

            # Decide if they are lead/client. Embudo realista: muchos más leads
            # que clientes cerrados (conversión ~25%), y la mitad quedan solo contacto.
            client_type = random.choice(["lead", "lead", "lead", "cliente", None, None, None])
            if client_type:
                cliente = Cliente(
                    telefono=phone,
                    numero_identificacion=str(random.randint(10000000, 99999999)),
                    nit_empresa=f"{random.randint(800000000, 999999999)}-{random.randint(0, 9)}",
                    tipo=client_type,
                    nombre_empresa=f"{random.choice(last_names)} & Asociados S.A.S.",
                    sector_empresa=random.choice(sectors),
                    actividad_empresa=random.choice(activities),
                    empleados_empresa=random.choice(employee_ranges),
                    creado_en=conv_time,
                    actualizado_en=conv_time
                )
                session.add(cliente)
                total_clients += 1

            # ¿Sigue abierta? Solo lo más reciente puede seguir viva; el resto está cerrado.
            is_open = (now - conv_time) < timedelta(hours=2) and random.random() < 0.5
            estado_conv = "abierta" if is_open else "cerrada"
            motivo_cierre = None if is_open else random.choice(["usuario", "inactividad", "usuario"])

            espera_desde = conv_time + timedelta(seconds=random.randint(10, 60))
            espera_hasta = None if is_open else (espera_desde + timedelta(seconds=random.randint(30, 900)))

            # Decide if conversation was escalated
            escalated = random.random() < 0.35  # 35% escalation rate
            radicado_id = None

            if escalated:
                # Pick area & agent
                area = random.choice(areas)
                agent_list = agents_by_area.get(area.id, [])
                agent = random.choice(agent_list) if agent_list else None

                # Un radicado se resuelve cuando cierra. Backlog realista: casos de
                # los últimos 7 días pueden seguir abiertos (escalado/en_cola) aunque
                # el chat con el bot haya cerrado; el resto ya está resuelto.
                reciente = (now - conv_time) < timedelta(days=7)
                sigue_abierto = is_open or (reciente and random.random() < 0.4)
                if sigue_abierto:
                    estado_rad = random.choice(["escalado", "escalado", "en_cola"])
                    resuelto_en = None
                else:
                    estado_rad = "resuelto"
                    # tiempo de atención: minutos a pocas horas tras el escalamiento
                    resuelto_en = conv_time + timedelta(minutes=random.randint(5, 480))

                radicado = Radicado(
                    telefono=phone,
                    area_id=area.id,
                    agente_id=agent.id if agent else None,
                    resumen=f"Solicitud de {area.nombre} sobre " + ("precios y licencias" if area.nombre == "comercial" else "error en módulo de facturación"),
                    estado=estado_rad,
                    modo=random.choice(["conectado", "notificacion"]),
                    email_enviado=random.choice([True, True, True, False]),  # ~75% notificado
                    # ~92% sincronizados con EspoCRM; el resto queda pendiente (fallo/latencia de sync)
                    crm_case_id=(("%017x" % random.randint(0, 16**17)) if random.random() < 0.92 else None),
                    resuelto_en=resuelto_en,
                    creado_en=conv_time,
                    actualizado_en=resuelto_en or conv_time
                )
                session.add(radicado)
                session.flush()  # To get the radicado.id

                # Set code
                radicado.codigo = f"ESC-{radicado.id}"
                radicado_id = radicado.id
                total_radicados += 1

            conversacion = Conversacion(
                telefono=phone,
                radicado_id=radicado_id,
                estado=estado_conv,
                tipo_solicitud=random.choice(["comercial", "soporte", "informacion"]),
                motivo_cierre=motivo_cierre,
                espera_desde=espera_desde,
                espera_hasta=espera_hasta,
                creado_en=conv_time,
                actualizado_en=conv_time
            )
            session.add(conversacion)
            session.flush()  # para conversacion.id
            total_conversations += 1

            # Mensajes: pares user/assistant (2 a 6) para poblar volumen y roles.
            n_turns = random.randint(1, 3)
            msg_t = conv_time
            for _ in range(n_turns):
                msg_t += timedelta(seconds=random.randint(5, 90))
                session.add(Mensaje(telefono=phone, conversacion_id=conversacion.id,
                                    role="user", content=random.choice(user_msgs), timestamp=msg_t))
                msg_t += timedelta(seconds=random.randint(2, 30))
                session.add(Mensaje(telefono=phone, conversacion_id=conversacion.id,
                                    role="assistant", content=random.choice(bot_msgs), timestamp=msg_t))
                total_messages += 2

        session.commit()

    print("\nGeneration Complete!")
    print(f"Total contacts generated: {total_contacts}")
    print(f"Total messages generated: {total_messages}")
    print(f"Total clients/leads generated: {total_clients}")
    print(f"Total radicados (escalations) generated: {total_radicados}")
    print(f"Total conversations generated: {total_conversations}")
    session.close()

if __name__ == "__main__":
    seed()
