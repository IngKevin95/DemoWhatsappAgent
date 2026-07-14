# Proposal: Botones Interactivos WhatsApp (EP-007)

## Problem

Actualmente el proveedor de Meta (`agent/providers/meta.py`) solo es capaz de enviar y recibir mensajes de texto (`type: text`). Para implementar el flujo de Habeas Data (EP-008), necesitamos que el sistema pueda enviar botones interactivos (Sí/No) y ser capaz de recibir y parsear la respuesta del usuario (payload del botón).

## Why

- **Requisito Técnico:** Sin botones no se puede crear un flujo determinista y fricción-cero para el consentimiento de tratamiento de datos.
- **Bloqueo Fase 2:** EP-007 es blocker técnico para el Gate de Habeas Data (EP-008).

## What Changes

1. **`agent/providers/meta.py`:**
   - Modificar/Agregar capacidad para enviar mensajes de tipo `interactive` (con sub-tipo `button`).
   - Modificar `parsear_webhook` para detectar el tipo `interactive` de los mensajes entrantes, extrayendo el `button_reply.id` o el título del botón como texto del mensaje.
2. **`agent/providers/base.py`:**
   - Podría ser necesario extender `enviar_mensaje` o crear un `enviar_botones` en la interfaz base, y su modelo de mensaje entrante para soportar payload estructurado, aunque un mapeo al atributo `texto` de `MensajeEntrante` puede ser suficiente si el `payload` se traduce directamente.

## Value

- Permite interacciones estructuradas con el usuario final (Botones), mejorando la UX y guiando flujos como la autorización de Habeas Data.
