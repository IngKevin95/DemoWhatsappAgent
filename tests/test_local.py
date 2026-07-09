"""Simulador de chat en terminal para probar SysBot sin WhatsApp.
Ejecutar: python -m tests.test_local"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from agent.brain import generar_respuesta  # noqa: E402
from agent.memory import guardar_mensaje, inicializar_db, obtener_historial  # noqa: E402

TELEFONO_TEST = "573000000000"


async def main():
    await inicializar_db()
    print("SysBot (Ctrl+C para salir)\n")
    while True:
        try:
            texto = input("Tú: ")
        except (KeyboardInterrupt, EOFError):
            break
        historial = await obtener_historial(TELEFONO_TEST)
        respuesta = await generar_respuesta(TELEFONO_TEST, texto, historial)
        await guardar_mensaje(TELEFONO_TEST, "user", texto)
        await guardar_mensaje(TELEFONO_TEST, "assistant", respuesta)
        print(f"SysBot: {respuesta}\n")


if __name__ == "__main__":
    asyncio.run(main())
