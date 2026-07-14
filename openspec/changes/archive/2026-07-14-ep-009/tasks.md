# Tasks: Clasificación de Flujo + Alta CRM (EP-009)

- [x] Implementar asíncronamente (o ignorando errores) el `crear_lead` en `agent/main.py` cuando se acepta el Habeas Data.
- [x] Implementar `clasificar_intencion` usando `google-genai` en `agent/brain.py`.
- [x] En `agent/main.py`, invocar `clasificar_intencion` cuando el `tipo_solicitud` de la Conversacion activa sea nulo, y actualizar la BD.
- [x] Refactorizar `escalar_a_humano` en `agent/tools.py` para reusar `radicado_id` si existe en la conversación, o crearlo y asignarlo si no.
- [x] Agregar tests para las tres funcionalidades anteriores.
