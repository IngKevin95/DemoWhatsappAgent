import asyncio
from dotenv import load_dotenv
load_dotenv()

from agent.brain_langchain import generar_respuesta, clasificar_intencion

async def main():
    print("Clasificando...")
    intent = await clasificar_intencion("Quiero comprar una licencia")
    print(f"Intent: {intent}")
    
    print("\nGenerando respuesta...")
    resp = await generar_respuesta("Hola, qu modulos tienes?", "123456789")
    print(f"Respuesta: {resp}")

if __name__ == "__main__":
    asyncio.run(main())