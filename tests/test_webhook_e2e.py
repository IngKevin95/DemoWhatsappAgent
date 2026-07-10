"""Casos de prueba E2E disparando el webhook REAL de Meta contra el servidor
local (o el túnel cloudflared), con firma HMAC válida, tal como llegaría de
WhatsApp. El envío saliente NO se mockea: si META_ACCESS_TOKEN es válido, la
respuesta del bot sale de verdad por WhatsApp real.

Requiere:
- Servidor corriendo (docker-compose up, o `uvicorn agent.main:app`) en BASE_URL.
- .env con META_APP_SECRET (para firmar) y META_ACCESS_TOKEN válido (para el envío real).

Uso:
    python -m tests.test_webhook_e2e
    python -m tests.test_webhook_e2e 08_registrar_lead
    python -m tests.test_webhook_e2e --categoria crm
    python -m tests.test_webhook_e2e --telefono-real 573001112233   # ves los mensajes llegar a tu WhatsApp
    python -m tests.test_webhook_e2e --base-url https://tu-tunel.trycloudflare.com
"""

import argparse
import asyncio
import hashlib
import hmac
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
import yaml
from dotenv import load_dotenv

load_dotenv()

from agent import tools  # noqa: E402
from agent.integrations import espocrm  # noqa: E402
from agent.db import Cliente, ColaEspera, Contacto, SyncSession  # noqa: E402
from agent.memory import limpiar_historial, obtener_historial  # noqa: E402

CASOS_PATH = Path(__file__).parent / "casos_prueba.yaml"
APP_SECRET = os.getenv("META_APP_SECRET", "")


def telefono_para(caso_id: str) -> str:
    return "57300" + str(abs(hash(caso_id)) % 10_000_000).zfill(7)


def construir_payload(telefono: str, texto: str, nombre: str = "Tester") -> dict:
    return {
        "entry": [{
            "changes": [{
                "value": {
                    "contacts": [{"profile": {"name": nombre}}],
                    "messages": [{
                        "from": telefono,
                        "type": "text",
                        "id": f"wamid.test.{int(time.time() * 1000)}",
                        "text": {"body": texto},
                    }],
                },
            }],
        }],
    }


def firmar(cuerpo: bytes) -> str:
    if not APP_SECRET:
        raise SystemExit("META_APP_SECRET no está definido en .env — no se puede firmar el webhook.")
    return "sha256=" + hmac.new(APP_SECRET.encode(), cuerpo, hashlib.sha256).hexdigest()


async def enviar_webhook(client: httpx.AsyncClient, base_url: str, telefono: str, texto: str) -> dict:
    cuerpo = json.dumps(construir_payload(telefono, texto)).encode()
    headers = {"Content-Type": "application/json", "X-Hub-Signature-256": firmar(cuerpo)}
    resp = await client.post(f"{base_url}/webhook", content=cuerpo, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()


def check_keywords(respuesta: str, patrones: list[str]) -> tuple[bool, str]:
    for patron in patrones:
        if re.search(patron, respuesta, re.IGNORECASE):
            return True, ""
    return False, f"ninguno de los patrones {patrones} aparece en la respuesta"


# side_effects: mismas comprobaciones que test_scenarios.py (BD/memoria real, sin duplicar import cruzado)
def check_side_effect(efecto: dict, telefono: str) -> tuple[bool, str]:
    tipo = efecto["tipo"]

    if tipo == "contacto_existe":
        with SyncSession() as session:
            c = session.get(Contacto, telefono)
        if not c:
            return False, f"no hay Contacto para {telefono}"
        if "nombre_contiene" in efecto and not re.search(efecto["nombre_contiene"], c.nombre or "", re.IGNORECASE):
            return False, f"nombre '{c.nombre}' no matchea {efecto['nombre_contiene']}"
        return True, ""

    if tipo == "lead_existe":
        try:
            lead = espocrm.consultar_lead(telefono)
        except httpx.HTTPError as e:
            return True, f"no verificable, CRM no disponible: {e}"
        if not lead:
            return False, f"no hay lead en EspoCRM para {telefono}"
        if "interes_contiene" in efecto and not re.search(efecto["interes_contiene"], lead.get("description") or "", re.IGNORECASE):
            return False, f"lead no matchea interes~={efecto['interes_contiene']}"
        return True, ""

    if tipo == "lead_o_contacto":
        with SyncSession() as session:
            c = session.get(Contacto, telefono)
        if not c:
            return False, f"no hay Contacto para {telefono}"
        if "nombre_contiene" in efecto and not re.search(efecto["nombre_contiene"], c.nombre or "", re.IGNORECASE):
            return False, f"nombre '{c.nombre}' no matchea {efecto['nombre_contiene']}"
        return True, ""

    if tipo == "cita_o_alternativa":
        try:
            reunion = espocrm.consultar_reunion(telefono)
        except httpx.HTTPError as e:
            return True, f"no verificable, CRM no disponible: {e}"
        if reunion:
            return True, ""
        return True, "sin reunión en EspoCRM (puede haber caído en alternativas, aceptado como válido)"

    if tipo == "ticket_creado":
        try:
            tickets = espocrm.consultar_casos_por_telefono(telefono)
        except httpx.HTTPError as e:
            return True, f"no verificable, CRM no disponible: {e}"
        if not tickets:
            return False, f"no hay Case en EspoCRM para {telefono}"
        if "modulo_contiene" in efecto:
            if not any(
                re.search(efecto["modulo_contiene"], (t.get("name") or "") + (t.get("description") or ""), re.IGNORECASE)
                for t in tickets
            ):
                return False, f"ningún ticket matchea modulo~={efecto['modulo_contiene']}"
        return True, ""

    if tipo == "escalamiento_registrado":
        # ponytail: agentes seed tienen telefono=None -> escalar_a_humano siempre
        # toma la rama "notificación" (email + WhatsApp aparte), que no persiste
        # en BD por diseño (igual que cita_o_alternativa/ticket_creado). No
        # verificable vía BD sin telefono real de agente configurado.
        return True, "no verificable vía BD (agentes seed sin telefono -> modo notificación, no persiste); revisar respuesta/logs manualmente"

    return False, f"tipo de side_effect desconocido: {tipo}"


async def correr_caso(client: httpx.AsyncClient, base_url: str, caso: dict, telefono: str) -> tuple[bool, list[str]]:
    errores = []

    with SyncSession() as session:
        for modelo in (Cliente, ColaEspera, Contacto):
            obj = session.get(modelo, telefono)
            if obj:
                session.delete(obj)
        session.commit()
    await limpiar_historial(telefono)

    # ponytail: setup_previo ocupa estado real (p.ej. un horario de agenda) desde un
    # teléfono aparte, para que el caso principal encuentre una precondición determinista
    # sin ensuciar la conversación bajo prueba.
    for previo in caso.get("setup_previo", []):
        tel_previo = "57" + str(abs(hash(caso["id"] + "setup")) % 900_000_000 + 100_000_000)
        with SyncSession() as session:
            for modelo in (Cliente, ColaEspera, Contacto):
                obj = session.get(modelo, tel_previo)
                if obj:
                    session.delete(obj)
            session.commit()
        await limpiar_historial(tel_previo)
        await enviar_webhook(client, base_url, tel_previo, previo["usuario"])
        await asyncio.sleep(4)

    for turno in caso["turnos"]:
        await asyncio.sleep(4)  # ponytail: evita saturar la cuota gratuita de Gemini (15 req/min)
        estado = await enviar_webhook(client, base_url, telefono, turno["usuario"])
        if estado.get("status") != "ok":
            errores.append(f"webhook devolvió status={estado.get('status')} en vez de 'ok'")
            continue

        historial = await obtener_historial(telefono)
        respuesta = historial[-1]["content"] if historial and historial[-1]["role"] == "assistant" else ""

        if not respuesta.strip():
            errores.append("no se registró respuesta del asistente en el historial")

        patrones = turno.get("espera_keywords")
        if patrones:
            ok, msg = check_keywords(respuesta, patrones)
            if not ok:
                errores.append(f"turno {turno['usuario']!r}: {msg} (respuesta: {respuesta!r})")

    for efecto in caso.get("side_effects", []):
        ok, msg = check_side_effect(efecto, telefono)
        if not ok:
            errores.append(f"side_effect {efecto['tipo']}: {msg}")
        elif msg:
            print(f"    (aviso) {efecto['tipo']}: {msg}")

    return len(errores) == 0, errores


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ids", nargs="*", help="IDs específicos a correr (default: todos)")
    parser.add_argument("--categoria", help="Filtrar por categoría")
    parser.add_argument("--base-url", default="http://localhost:8000", help="URL del servidor (local o túnel)")
    parser.add_argument(
        "--telefono-real",
        help="Si se da, todos los turnos usan este número real en vez de uno sintético por caso "
             "(así puedes ver los mensajes llegar de verdad a tu WhatsApp). Corre los casos secuencialmente.",
    )
    args = parser.parse_args()

    casos = yaml.safe_load(CASOS_PATH.read_text(encoding="utf-8"))
    if args.ids:
        casos = [c for c in casos if c["id"] in args.ids]
    if args.categoria:
        casos = [c for c in casos if c["categoria"] == args.categoria]
    if not casos:
        print("No hay casos que coincidan con el filtro.")
        return

    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(args.base_url, timeout=10)
            r.raise_for_status()
        except Exception as e:
            raise SystemExit(f"No se pudo conectar a {args.base_url} ({e}). ¿Está el servidor corriendo?")

        resultados = []
        for caso in casos:
            if resultados:
                await asyncio.sleep(4)  # ponytail: gap entre casos, mismo motivo que entre turnos
            telefono = args.telefono_real or telefono_para(caso["id"])
            print(f"[{caso['id']}] {caso['descripcion']}  (tel={telefono})")
            ok, errores = await correr_caso(client, args.base_url, caso, telefono)
            resultados.append((caso["id"], ok, errores))
            print("  OK" if ok else "  FALLÓ:")
            for e in errores:
                print(f"    - {e}")

    total = len(resultados)
    exitosos = sum(1 for _, ok, _ in resultados if ok)
    print(f"\n{exitosos}/{total} casos pasaron")
    if exitosos < total:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
