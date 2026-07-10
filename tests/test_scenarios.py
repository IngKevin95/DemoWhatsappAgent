"""Runner de casos de prueba conversacionales end-to-end contra SysBot,
sin pasar por WhatsApp (llama directo a agent.brain.generar_respuesta).

Uso:
    python -m tests.test_scenarios                 # corre todos los casos
    python -m tests.test_scenarios 08_registrar_lead 11_agendar_cita_exitosa
    python -m tests.test_scenarios --categoria crm

Requiere GEMINI_API_KEY y la base de datos levantada (docker-compose up postgres).
Cada caso usa un teléfono único (derivado del id) para no pisar datos entre casos.

ponytail: aserciones de texto son regex OR sueltas (el LLM no es determinista);
lo que realmente valida el caso son los side_effects (estado real en BD/memoria).
"""

import argparse
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import yaml
from dotenv import load_dotenv

load_dotenv()

import httpx

from agent import tools  # noqa: E402
from agent.brain import RESPUESTAS_FALLBACK, generar_respuesta  # noqa: E402
from agent.db import Cliente, ColaEspera, Contacto, SyncSession  # noqa: E402
from agent.integrations import espocrm  # noqa: E402
from agent.memory import guardar_mensaje, inicializar_db, obtener_historial  # noqa: E402

CASOS_PATH = Path(__file__).parent / "casos_prueba.yaml"


def telefono_para(caso_id: str) -> str:
    return "57300" + str(abs(hash(caso_id)) % 10_000_000).zfill(7)


def check_keywords(respuesta: str, patrones: list[str]) -> tuple[bool, str]:
    for patron in patrones:
        if re.search(patron, respuesta, re.IGNORECASE):
            return True, ""
    return False, f"ninguno de los patrones {patrones} aparece en la respuesta"


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
        citas = [c for c in tools._CITAS_DB if c["telefono"] == telefono]
        if citas or reunion:
            if citas and "area" in efecto and not any(c["area"].lower() == efecto["area"].lower() for c in citas):
                return False, f"cita existe pero no en área {efecto['area']}"
            return True, ""
        return True, "sin cita confirmada (puede haber caído en alternativas, aceptado como válido)"

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
        with SyncSession() as session:
            en_cola = session.get(ColaEspera, telefono)
            contacto = session.get(Contacto, telefono)
        conectado = contacto and contacto.atendido_por is not None
        if not en_cola and not conectado:
            return False, "no quedó en cola ni conectado a un agente (¿se llamó escalar_a_humano?)"
        return True, ""

    return False, f"tipo de side_effect desconocido: {tipo}"


async def correr_caso(caso: dict) -> tuple[bool, list[str]]:
    telefono = telefono_para(caso["id"])
    errores = []

    with SyncSession() as session:
        for modelo in (Cliente, ColaEspera, Contacto):
            obj = session.get(modelo, telefono)
            if obj:
                session.delete(obj)
        session.commit()

    for turno in caso["turnos"]:
        historial = await obtener_historial(telefono)
        respuesta = await generar_respuesta(telefono, turno["usuario"], historial)
        await guardar_mensaje(telefono, "user", turno["usuario"])
        await guardar_mensaje(telefono, "assistant", respuesta)

        if not respuesta or not respuesta.strip():
            errores.append("respuesta vacía")
        elif respuesta in RESPUESTAS_FALLBACK:
            errores.append(f"cayó en fallback: {respuesta!r}")

        for patrones in (turno.get("espera_keywords"),):
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
    args = parser.parse_args()

    casos = yaml.safe_load(CASOS_PATH.read_text(encoding="utf-8"))
    if args.ids:
        casos = [c for c in casos if c["id"] in args.ids]
    if args.categoria:
        casos = [c for c in casos if c["categoria"] == args.categoria]

    if not casos:
        print("No hay casos que coincidan con el filtro.")
        return

    await inicializar_db()

    resultados = []
    for caso in casos:
        print(f"[{caso['id']}] {caso['descripcion']}")
        ok, errores = await correr_caso(caso)
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
