# Spec: Botones Interactivos WhatsApp (EP-007)

## Feature Description
Habilitar la capacidad de enviar mensajes con botones interactivos y recibir respuestas de botones, principalmente para implementar el gate de Habeas Data (Sí/No).

## Requirements

1. **`agent/providers/base.py`:**
   - La clase `ProveedorMensajeria` debe soportar una manera de enviar botones. Se puede usar un argumento opcional `botones: list[dict]` en `enviar_mensaje`, o bien tener un método `enviar_mensaje_interactivo`. Usaremos `botones: list[dict] = None` en `enviar_mensaje` para retrocompatibilidad, donde cada botón es `{"id": "...", "title": "..."}`.

2. **`agent/providers/meta.py`:**
   - **`enviar_mensaje`**: Si `botones` no es None, formatear el payload como `"type": "interactive"`, `"interactive": {"type": "button", "body": {"text": mensaje}, "action": {"buttons": [...]}}`.
   - **`parsear_webhook`**: Detectar `"type": "interactive"` y `"interactive": {"type": "button_reply"}`. En este caso, extraer `button_reply.id` y mapearlo al campo `texto` o `payload` de `MensajeEntrante`. Por simplicidad para el resto del sistema, si es un button reply, su `texto` será el `id` o el `title` del botón.
   - Máximo 3 botones permitidos por la API de WhatsApp. El límite será validado.

3. **`agent/main.py`:**
   - Crear una función helper `enviar_botones_seguro(telefono: str, mensaje: str, botones: list[dict])` similar a `enviar_mensaje_seguro`.

## Context Links
- EP-008: Habeas Data Gate (requiere botones).
