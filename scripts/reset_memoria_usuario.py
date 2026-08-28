import os
import asyncio
import sys

# Configurar URL de BD para ejecución local desde el host si no está definida
if not os.environ.get("DATABASE_URL") or "@postgres:" in os.environ.get("DATABASE_URL", ""):
    os.environ["DATABASE_URL"] = "postgresql://demobot:demobot@localhost:5441/demobot"

# Asegurar que se puede importar el módulo agent
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.memory import obtener_conversacion_activa, cerrar_conversacion, limpiar_historial

# === CAMBIA EL NÚMERO DE TELÉFONO AQUÍ ===
TELEFONO = "573213336960"
# ========================================

async def main():
    print(f"Iniciando limpieza para el teléfono: {TELEFONO}...")
    
    # 1. Eliminar todos los mensajes del historial
    await limpiar_historial(TELEFONO)
    print("Mensajes del historial eliminados con éxito.")
    
    # 2. Obtener y cerrar conversación activa
    conv_id = await obtener_conversacion_activa(TELEFONO)
    if conv_id:
        await cerrar_conversacion(conv_id)
        print(f"Conversación activa ID {conv_id} marcada como cerrada.")
    else:
        print("No se encontraron conversaciones activas abiertas para este número.")
        
    print("Proceso completado exitosamente.")

if __name__ == "__main__":
    asyncio.run(main())
