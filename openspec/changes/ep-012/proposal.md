# Change Proposal: Soporte Multi-canal (Telegram)

## Por qué
Actualmente, DemoWhatsappAgent está fuertemente acoplado a Meta API. Dependemos exclusivamente de un proveedor, lo cual representa un single point of failure y reduce nuestro mercado direccionable para aquellos clientes que prefieren canales alternativos como Telegram.

## Qué cambia
Se creará un nuevo proveedor `agent/providers/telegram.py` que implemente la clase base `ProveedorWhatsApp` (que idealmente pasará a llamarse `ProveedorMensajeria`). También se habilitará en `main.py` un nuevo endpoint `/webhook/telegram` capaz de instanciar y usar este proveedor en lugar del de Meta para la entrada de datos, y el sistema orquestador sabrá inyectar el proveedor adecuado para las respuestas.

## Capacidades

1. **Recibir Webhooks de Telegram:** Parseo de payloads de Telegram a `MensajeEntrante`.
2. **Enviar Mensajes a Telegram:** Enviar respuestas a través del Bot API de Telegram.
3. **Orquestación Multi-canal:** Instanciar dinámicamente el proveedor basado en el canal y guardarlo en el contexto.

## Impacto
- **Archivos modificados:** `agent/main.py` (nuevo router), `agent/providers/telegram.py` (nuevo archivo), `agent/providers/base.py` (posible renombramiento o ajustes menores).
- **Dependencias:** Requerirá el token del bot de Telegram en las variables de entorno (`TELEGRAM_BOT_TOKEN`).

## Trazabilidad
- **Épica:** EP-012
- **Historias de Usuario:**
  - HU-051
  - HU-052
