# Propuesta de Cambio: ep-006 (Modelo Conversación + Consentimiento)

## ¿Por qué hacemos este cambio?
El modelo de dominio define que cada interacción sigue la jerarquía `Radicado → Conversación → Mensaje`. Actualmente, esta jerarquía está incompleta en base de datos (`Mensaje` se liga directamente por teléfono). Además, no hay persistencia del consentimiento de habeas data, lo cual es obligatorio legalmente antes de capturar datos personales en WhatsApp.

## ¿Qué cambia?
- Se creará la tabla `conversaciones` en base de datos.
- Los mensajes estarán ligados por foreign key a la `conversacion_id` respectiva.
- Las conversaciones estarán ligadas a `radicado_id`.
- Se agregarán columnas de consentimiento a la tabla `contactos` o en la persistencia del cliente.
- Se implementarán helpers en la capa de memoria para abrir y cerrar conversaciones.

## Capacidades Afectadas
- **Base de Datos:** Nuevas tablas y columnas.
- **Memoria del Agente:** Adaptación de las consultas y asociaciones.

## Impacto
- `agent/db.py` (modelos de SQLAlchemy).
- `agent/memory.py` (helpers de persistencia y contexto de conversación).
- Migración de la base de datos (creación de la tabla).

## Trazabilidad
- **Épica:** EP-006 (Modelo Conversación + Consentimiento)
- **Historias de Usuario:**
  - HU-034: Entidad Conversación (abrir/cerrar)
  - HU-035: Cada mensaje ligado a su conversación
  - HU-036: Consentimiento persistido en el contacto
  - HU-037: Conversación ligada a su radicado
