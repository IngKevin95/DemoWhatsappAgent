import asyncio
from agent.memory import obtener_conversacion_activa, cerrar_conversacion, limpiar_historial

async def main():
    telefono = "573213336960"
    # Deletete messages
    await limpiar_historial(telefono)
    print("Messages cleared.")
    
    # Close active conversation
    id = await obtener_conversacion_activa(telefono)
    if id:
        await cerrar_conversacion(id)
        print(f"Active conversation {id} closed.")
    else:
        print("No active conversation found.")

if __name__ == "__main__":
    asyncio.run(main())
