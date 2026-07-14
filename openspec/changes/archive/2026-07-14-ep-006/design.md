# Diseño Técnico: Modelo Conversación

## ADR-003: Separación de Conversación y Mensaje
**Decisión:** Se agregará la entidad `Conversacion` entre `Contacto` y `Mensaje`.
**Razón:** Para cumplir con el modelo de dominio y permitir el gate de habeas data, así como el cierre e inactividad, necesitamos persistir el estado de la sesión, no solo de los mensajes individuales.

## Cambios de Arquitectura
1. Crear tabla `conversaciones` (`id`, `telefono`, `radicado_id`, `estado`, `tipo_solicitud`).
2. Actualizar `agent/db.py` y `agent/memory.py` para abstraer operaciones de abrir/cerrar.
