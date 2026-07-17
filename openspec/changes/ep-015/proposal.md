# Change Proposal: Resiliencia de Escalamiento y Notificaciones a Líderes

## Por qué
En producción, un cliente recibió un mensaje improvisado por el LLM ("Nota: Estoy teniendo un
inconveniente técnico momentáneo...") sin que quedara ningún rastro en `docker logs`. El
diagnóstico dentro del contenedor confirmó `google.auth.exceptions.RefreshError: invalid_grant:
Token has been expired or revoked.` en `consultar_disponibilidad_agenda` -> `horarios_libres` ->
`get_calendar_service` -> `_credentials().refresh()`. El `except` de la tool solo actúa si
`_es_error_de_cuota_google(e)` es `True`; como un `RefreshError` no es error de cuota, se relanza
con `raise` sin log, sin escalamiento y sin alerta. Además, cuando un caso queda en cola porque
todos los agentes de un área están ocupados, nadie del liderazgo se entera hasta que alguien revisa
manualmente — no hay notificación proactiva.

## Qué cambia
1. Generalizar el manejo de fallos de Google/Calendar en las tools que lo usan
   (`consultar_disponibilidad_agenda`, `agendar_cita`) para que **cualquier** excepción de Google
   (no solo cuota) dispare `logger.exception` + el flujo log/escalar/alertar-infra, preservando el
   comportamiento actual para errores de cuota sin duplicar notificaciones.
2. Nuevo parámetro `whatsapp_lider_infra`: ante un fallo técnico de Google, además del correo a
   infra ya existente, se envía un WhatsApp directo a ese número. Si el parámetro no existe o está
   vacío, se loguea y el resto del flujo continúa sin bloquear.
3. Nuevo parámetro por área `whatsapp_lider_<area>`: en la rama "todos ocupados -> cola" de
   `escalar_a_humano`, se notifica por WhatsApp al líder comercial del área con código de caso,
   nombre del cliente y posición en cola. No aplica cuando el caso se asigna directo a un agente
   libre.

## Capacidades
1. **Manejo generalizado de fallos de Google** (`_manejar_fallo_google`, generaliza a
   `_manejar_error_cuota_google`): todo fallo de Google en las tools de Calendar queda logueado y
   dispara escalamiento + alerta a infra.
2. **Notificación WhatsApp a líder de infraestructura**: alerta directa además del correo, resiliente
   a fallos de envío y a parámetro ausente.
3. **Notificación WhatsApp a líder comercial por área en cola**: alerta proactiva solo en la rama de
   encolamiento, resiliente a fallos de envío y a parámetro ausente.

## Impacto
- **Archivos modificados**: `agent/tools.py` (`_es_error_de_cuota_google`,
  `_manejar_error_cuota_google` -> `_manejar_fallo_google`, `agendar_cita`,
  `consultar_disponibilidad_agenda`, `escalar_a_humano`), `scripts/seed_db.py` (seed de los nuevos
  parámetros — es la fuente real de seed de `parametros`, `init-db/schema.sql` solo define el
  esquema de la tabla).
- **Dependencias**: ninguna nueva; reutiliza `_enviar_whatsapp_directo` y `enviar_email` ya
  existentes.
- **Datos**: dos claves nuevas en `parametros` (`whatsapp_lider_infra`, `whatsapp_lider_<area>` por
  cada área configurada, p.ej. `whatsapp_lider_comercial`, `whatsapp_lider_soporte`).

## Trazabilidad
- **Épica:** EP-015
- **Historias de Usuario:**
  - HU-057
  - HU-058
  - HU-059
