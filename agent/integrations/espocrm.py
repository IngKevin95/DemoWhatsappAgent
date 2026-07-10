import os
from datetime import datetime, timedelta
from functools import lru_cache

import httpx

BASE_URL = os.getenv("ESPOCRM_URL", "http://espocrm")
API_KEY = os.getenv("ESPOCRM_API_KEY", "")
TIMEOUT = 5.0


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


def crear_lead(nombre: str, telefono: str, empresa: str, correo: str, interes: str) -> dict:
    body = {
        "lastName": nombre,
        "phoneNumber": _e164(telefono),
        "accountName": empresa,
        "emailAddress": correo,
        "description": interes,
    }
    r = httpx.post(f"{BASE_URL}/api/v1/Lead", json=body, headers=_headers(), timeout=TIMEOUT)
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


def consultar_reunion(telefono: str) -> dict | None:
    params = {"where[0][type]": "contains", "where[0][attribute]": "description", "where[0][value]": telefono}
    r = httpx.get(f"{BASE_URL}/api/v1/Meeting", params=params, headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    lista = r.json().get("list", [])
    return lista[0] if lista else None


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
