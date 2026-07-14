# Proposal: Gate de Consentimiento Habeas Data (EP-008)

## Problem

Actualmente, el flujo del webhook en `agent/main.py` aunque intercepta el Habeas Data (hecho en EP-006) pidiendo responder "SI" o "NO" con texto libre, no utiliza los botones interactivos desarrollados en EP-007, y el flujo es menos guiado. Es un requerimiento legal capturar este consentimiento sin fricción antes de procesar cualquier dato personal en el LLM.

## Why

- **Cumplimiento legal:** Capturar/registrar PII sin autorización previa es ilegal.
- **Fricción Cero:** Requerir que el usuario escriba "SI" o "NO" es propenso a errores. El uso de botones (EP-007) mejora la conversión y elimina la ambigüedad en el parsing de la respuesta.
- **Flujo Determinado:** Bloquea EP-009 y EP-010 si el usuario no aprueba el consentimiento explícitamente.

## What Changes

1. **`agent/main.py`:**
   - En `recibir_webhook`, cuando `consentimiento_dado` sea `False`, se enviará el saludo + políticas de privacidad usando `enviar_mensaje_seguro` con el parámetro `botones` apuntando a las opciones `{"id": "SI", "title": "Sí, acepto"}` y `{"id": "NO", "title": "No, gracias"}`.
   - El parseo de la respuesta para el gate verificará directamente que el `mensaje.texto` recibido corresponda a `"SI"` o `"NO"`, aprovechando que la API de Meta devolverá el `id` del botón cuando sea presionado (garantizado por EP-007).

## Value

- Cumplimiento de leyes de privacidad de datos (Habeas Data).
- Confianza del usuario.
- Mejor experiencia de usuario al usar botones nativos de WhatsApp.
