# Design: EP-015 Resiliencia de Escalamiento y Notificaciones a Líderes

## Contexto
`agent/tools.py` centraliza el manejo de fallos de Google detrás de
`_es_error_de_cuota_google(e)` + `_manejar_error_cuota_google(...)`. Tres sitios de llamada dentro
de `agendar_cita` y uno en `consultar_disponibilidad_agenda` hacen `if _es_error_de_cuota_google(e):
... else: raise`, dejando escapar sin log cualquier fallo que no matchee las heurísticas de cuota
(HttpError 403/429 con keywords, o strings de rate limit). `escalar_a_humano` ya tiene la rama de
cola (todos ocupados) donde hoy no se notifica a nadie del liderazgo.

## Decisión: generalizar sin perder la distinción de cuota
- `_manejar_error_cuota_google` se renombra a `_manejar_fallo_google(e, area, telefono, nombre,
  resumen)`. Sigue haciendo `logger.exception` + correo a infra + escalamiento; se le agrega el
  paso de WhatsApp a `whatsapp_lider_infra` (HU-058).
- Los 4 sitios de llamada cambian de `if _es_error_de_cuota_google(e): ... else: raise` a
  `_manejar_fallo_google(...)` incondicional (cualquier `Exception` de Google cae ahí), eliminando
  el `raise` silencioso. `_es_error_de_cuota_google` se conserva solo si se necesita distinguir el
  mensaje al usuario entre cuota y otro fallo — en la práctica el mensaje ya es genérico
  ("Servicio temporalmente inactivo..."), así que no hace falta bifurcar la respuesta.
- No se duplica notificación: `_manejar_fallo_google` sigue siendo el único punto que envía
  correo/WhatsApp/escala, se llama una sola vez por excepción capturada.

## Decisión: parámetros de líderes vía tabla `parametros`
- `whatsapp_lider_infra` (clave global) y `whatsapp_lider_<area>` (una clave por área, ej.
  `whatsapp_lider_comercial`) se leen con la misma función `_get_parametro(clave)` ya usada en el
  resto de tools.py (ver `_obtener_horario_atencion`). Ausencia o vacío = no enviar, solo loguear.
- El seed real vive en `scripts/seed_db.py::PARAMETROS` (dict que puebla la tabla de forma
  idempotente) — `init-db/schema.sql` solo declara el esquema de la tabla `parametros`, no hace
  seed de datos. Se agregan las claves nuevas ahí para mantener el patrón existente del repo, en
  vez de escribir un INSERT directo en schema.sql que quedaría desincronizado del flujo real de
  arranque.

## Decisión: WhatsApp a líder comercial solo en la rama de cola
- Se agrega el envío dentro de la rama `# todos ocupados -> cola` de `escalar_a_humano`, después de
  calcular `delante` (posición en cola) y antes del `return`. Envuelto en try/except propio
  (`logger.error`, no interrumpe) para no afectar la respuesta al cliente si el WhatsApp falla.
- La rama de asignación directa a agente libre (`if libres:`) no se toca — ahí no se notifica al
  líder, por diseño (HU-059 Scenario 2).

## Alternativas descartadas
- Crear un servicio de notificaciones separado: sobre-ingeniería para 2 puntos de envío puntuales;
  se prefiere reutilizar `_enviar_whatsapp_directo` inline como ya hace `escalar_a_humano` con los
  agentes de opción A.
- Un solo parámetro `whatsapp_lideres` con JSON de todas las áreas: rompe el patrón actual de
  claves planas 1:1 en `parametros` (ver `whatsapp_numero_bot`, `correo_comercial`, etc.).
