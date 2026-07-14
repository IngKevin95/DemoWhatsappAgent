# Tasks: Botones Interactivos WhatsApp (EP-007)

- [x] Modificar `agent/providers/base.py` para soportar parámetro `botones` en `enviar_mensaje`.
- [x] Modificar `agent/providers/meta.py` -> `enviar_mensaje` para procesar botones (`interactive` type).
- [x] Modificar `agent/providers/meta.py` -> `parsear_webhook` para extraer `interactive.button_reply`.
- [x] Agregar `enviar_botones_seguro` en `agent/main.py`.
- [x] Agregar tests unitarios en `tests/unit/test_meta.py` para validar la construcción de payload y el parseo de webhooks.
