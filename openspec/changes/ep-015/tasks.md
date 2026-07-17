# Tasks: EP-015

## HU-057 — Manejo generalizado de fallos de Google
- [ ] Renombrar/generalizar `_manejar_error_cuota_google` -> `_manejar_fallo_google` en `agent/tools.py`
- [ ] `consultar_disponibilidad_agenda`: reemplazar `if _es_error_de_cuota_google(e): ... else: raise` por manejo incondicional
- [ ] `agendar_cita` (3 sitios: horarios_libres, crear_evento_calendar, enviar_email): mismo reemplazo
- [ ] Tests: RefreshError, error genérico no-cuota, error de cuota (regresión), happy path

## HU-058 — WhatsApp a líder de infraestructura
- [ ] Leer parámetro `whatsapp_lider_infra` dentro de `_manejar_fallo_google`
- [ ] Enviar WhatsApp vía `_enviar_whatsapp_directo` envuelto en try/except propio
- [ ] Loguear cuando el parámetro no existe/está vacío
- [ ] Seed `whatsapp_lider_infra` en `scripts/seed_db.py::PARAMETROS`
- [ ] Tests: configurado, no configurado, fallo de envío

## HU-059 — WhatsApp a líder comercial en cola
- [ ] Leer parámetro `whatsapp_lider_<area>` en la rama "todos ocupados -> cola" de `escalar_a_humano`
- [ ] Enviar WhatsApp con caso_id, nombre, posición en cola; try/except propio
- [ ] Seed `whatsapp_lider_comercial` / `whatsapp_lider_soporte` en `scripts/seed_db.py::PARAMETROS`
- [ ] Tests: encolado con líder configurado, asignación directa (sin notificar), sin parámetro, fallo de envío

## Cierre
- [ ] Suite completa verde (`pytest tests/unit/test_tools.py tests/unit/test_tools_additional.py`)
- [ ] `wiring_checklist[]` en build-state.json todo en `passing` con evidencia
- [ ] `wiring-adversarial-verifier` aprueba
