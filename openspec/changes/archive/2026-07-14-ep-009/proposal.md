# Proposal: Clasificación de Flujo + Alta CRM (EP-009)

## Problem

Actualmente:
1. El enrutamiento de la intención (soporte vs comercial) ocurre implícitamente en el LLM y no se guarda en la base de datos, perdiendo trazabilidad.
2. Los leads solo se crean en el CRM si el modelo invoca una tool explícita, perdiendo leads potenciales que no llegan a esa fase.
3. Cada vez que el bot escala a humano, crea un nuevo Radicado, incluso si ocurre en la misma conversación.

## Why

- **Trazabilidad:** Sin persistir el `tipo_solicitud` en la base de datos, no se pueden generar reportes de volumen por área.
- **Captura de Leads:** Cualquier usuario que acepta el tratamiento de datos debe quedar registrado en el CRM inmediatamente para campañas futuras.
- **Consistencia de Datos:** Una única conversación debe equivaler a un único Radicado (ticket) si se escala a un humano. Múltiples radicados por la misma sesión confunden a los agentes.

## What Changes

1. **Alta CRM Automática:** En `agent/main.py`, cuando el usuario responde "SI" al Habeas Data, se invoca a `EspoCRM.crear_lead` para registrar su teléfono inmediatamente.
2. **Clasificación Determinista:** Cuando el usuario envía su primer mensaje post-consentimiento, se invoca `clasificar_intencion` (que pasaremos a usar Gemini real o un prompt dedicado si no lo estaba) y se guarda el resultado en `Conversacion.tipo_solicitud`.
3. **Radicado Único:** En `agent/tools.py` (`escalar_a_humano`), se busca la conversación activa. Si ya tiene un `radicado_id`, se reusa ese Radicado. Si no, se crea uno nuevo y se actualiza la Conversación.

## Value

- Mejora la calidad de datos y reportes.
- Aumenta el funnel de leads registrados en el CRM.
- Mejora la experiencia del agente humano al consolidar escalamientos en un solo ticket.
