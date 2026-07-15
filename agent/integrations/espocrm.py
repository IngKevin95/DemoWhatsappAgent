import os
import re
from datetime import datetime, timedelta
from functools import lru_cache

import httpx
from agent.utilities.retry import retry

BASE_URL = os.getenv("ESPOCRM_URL", "http://espocrm")
API_KEY = os.getenv("ESPOCRM_API_KEY", "")
TIMEOUT = 5.0

# EspoCRM valida emailAddress estricto: un valor mal formado (lo que a veces
# extrae el LLM) hace 400 y tumba la creación del lead. Se omite si no es válido.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _headers() -> dict:
    return {"X-Api-Key": API_KEY}


@lru_cache
def _assigned_user_id() -> str:
    # ponytail: Meeting/Task exigen assignedUser; usamos el propio usuario de la API key.
    r = httpx.get(f"{BASE_URL}/api/v1/App/user", headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()["user"]["id"]


def _e164(telefono: str) -> str:
    # ponytail: EspoCRM valida phoneNumber estricto; wa_id de Meta llega sin '+'.
    return telefono if telefono.startswith("+") else f"+{telefono}"


def _componer_descripcion(interes: str, sector, actividad, empleados, identificacion, nit) -> str:
    """El Lead de EspoCRM no tiene campos para cédula/NIT/sector/actividad/empleados.
    Se vuelcan en description como bloque estructurado para que TODO viaje al CRM."""
    lineas = [interes] if interes else []
    perfil = [
        ("Identificación", identificacion), ("NIT empresa", nit),
        ("Sector", sector), ("Actividad", actividad), ("Empleados", empleados),
    ]
    detalle = [f"{k}: {v}" for k, v in perfil if v]
    if detalle:
        lineas.append("--- Perfil ---\n" + "\n".join(detalle))
    return "\n\n".join(lineas)


# FIX-REPAIR-003: Apply retry decorator for consistency with Google integration
@retry(max_attempts=3, backoff_base=2.0, exceptions=(Exception,))
def crear_lead(
    nombre: str, telefono: str, empresa: str, correo: str, interes: str,
    sector: str | None = None, actividad: str | None = None, empleados: str | None = None,
    identificacion: str | None = None, nit: str | None = None, ciudad: str | None = None,
) -> dict:
    """Upsert de Lead por teléfono: si ya existe lo actualiza (enriquece), si no lo crea.
    Manda TODOS los datos recolectados: correo->emailAddress, ciudad->addressCity, y
    cédula/NIT/sector/actividad/empleados en description (el Lead no tiene campos propios)."""
    existente = consultar_lead(telefono)
    # Al enriquecer un lead ya creado (p.ej. registrar_cliente añade cédula) sin
    # interes nuevo, preservar el interes original que ya vive en su description.
    if existente and not interes:
        interes = (existente.get("description") or "").split("\n\n--- Perfil ---")[0]

    body = {
        "lastName": nombre,
        "phoneNumber": _e164(telefono),
        "accountName": empresa,
        "description": _componer_descripcion(interes, sector, actividad, empleados, identificacion, nit),
    }
    # Solo enviar email si es un email válido; EspoCRM rechaza (400) uno mal formado.
    if correo and _EMAIL_RE.match(correo.strip()):
        body["emailAddress"] = correo.strip()
    if ciudad:
        body["addressCity"] = ciudad
    body = {k: v for k, v in body.items() if v not in (None, "")}

    if existente:
        r = httpx.put(f"{BASE_URL}/api/v1/Lead/{existente['id']}", json=body, headers=_headers(), timeout=TIMEOUT)
    else:
        r = httpx.post(f"{BASE_URL}/api/v1/Lead", json=body, headers=_headers(), timeout=TIMEOUT)
        # 409 = EspoCRM detectó duplicado por nombre/email (no por teléfono). Recuperar
        # el existente por teléfono y actualizarlo; si no hay match, devolverlo tal cual.
        if r.status_code == 409:
            prev = consultar_lead(telefono)
            if not prev:
                return {}
            r = httpx.put(f"{BASE_URL}/api/v1/Lead/{prev['id']}", json=body, headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def consultar_lead(telefono: str) -> dict | None:
    params = {"where[0][type]": "equals", "where[0][attribute]": "phoneNumber", "where[0][value]": _e164(telefono)}
    r = httpx.get(f"{BASE_URL}/api/v1/Lead", params=params, headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    lista = r.json().get("list", [])
    return lista[0] if lista else None


def consultar_casos_por_telefono(telefono: str) -> list[dict]:
    params = {"where[0][type]": "contains", "where[0][attribute]": "name", "where[0][value]": telefono}
    r = httpx.get(f"{BASE_URL}/api/v1/Case", params=params, headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json().get("list", [])


@retry(max_attempts=3, backoff_base=2.0, exceptions=(Exception,))
def crear_caso(telefono: str, descripcion: str, modulo: str) -> dict:
    body = {
        "name": f"Soporte {modulo} - {telefono}",
        "description": descripcion,
        "type": "Problem",
        "status": "New",
    }
    r = httpx.post(f"{BASE_URL}/api/v1/Case", json=body, headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def consultar_caso(caso_id: str) -> dict:
    r = httpx.get(f"{BASE_URL}/api/v1/Case/{caso_id}", headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def comentar_caso(caso_id: str, texto: str) -> dict:
    body = {"type": "Post", "parentType": "Case", "parentId": caso_id, "post": texto}
    r = httpx.post(f"{BASE_URL}/api/v1/Note", json=body, headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def actualizar_estado_caso(caso_id: str, status: str) -> dict:
    r = httpx.put(f"{BASE_URL}/api/v1/Case/{caso_id}", json={"status": status}, headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def consultar_reunion(telefono: str) -> dict | None:
    params = {"where[0][type]": "contains", "where[0][attribute]": "description", "where[0][value]": telefono}
    r = httpx.get(f"{BASE_URL}/api/v1/Meeting", params=params, headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    lista = r.json().get("list", [])
    return lista[0] if lista else None


@retry(max_attempts=3, backoff_base=2.0, exceptions=(Exception,))
def crear_reunion(nombre: str, telefono: str, motivo: str, fecha: str, hora: str, duracion_min: int = 30) -> dict:
    inicio = f"{fecha} {hora}:00"
    fin = f"{fecha} {(datetime.strptime(hora, '%H:%M') + timedelta(minutes=duracion_min)).strftime('%H:%M')}:00"
    body = {
        "name": f"{motivo} - {nombre}",
        "description": f"Contacto: {nombre} ({telefono})",
        "dateStart": inicio,
        "dateEnd": fin,
        "status": "Planned",
        "assignedUserId": _assigned_user_id(),
    }
    r = httpx.post(f"{BASE_URL}/api/v1/Meeting", json=body, headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def crear_tarea(nombre: str, descripcion: str, fecha_vencimiento: str | None = None) -> dict:
    body = {"name": nombre, "description": descripcion, "status": "Not Started", "assignedUserId": _assigned_user_id()}
    if fecha_vencimiento:
        # ponytail: Task.dateEnd exige datetime, no solo fecha
        body["dateEnd"] = f"{fecha_vencimiento} 23:59:59"
    r = httpx.post(f"{BASE_URL}/api/v1/Task", json=body, headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()
