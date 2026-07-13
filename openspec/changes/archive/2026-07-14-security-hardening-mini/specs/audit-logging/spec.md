# Specification: Audit Logging

Registrar todas las decisiones críticas (escalar a humano, agendar cita, consultar licencia, reclasificar caso) en tabla de auditoría con user_id, tool, timestamp, resultado.

## ADDED Requirements

### Requirement: Audit Log Table
El sistema SHALL mantener tabla `audit_logs` con campos: id, user_id, user_phone, tool_name, timestamp, action, result, metadata_json, error_msg, created_at.

#### Scenario: Audit table exists
- **WHEN** aplicación inicia
- **THEN** tabla `audit_logs` existe en Postgres con schema correcto
- **AND** índices en (user_id, tool_name, timestamp) para queries rápidas

### Requirement: Escalar a Humano Audit
El sistema SHALL loguear cada invocación de `escalar_a_humano()` con quién escaló, cuándo, resultado.

#### Scenario: Escalation logged on success
- **WHEN** usuario invoca "Quiero hablar con un agente" → tool `escalar_a_humano()` ejecuta exitosamente
- **THEN** audit table registra:
  - user_id: ID WhatsApp usuario
  - user_phone: teléfono usuario
  - tool_name: "escalar_a_humano"
  - timestamp: ISO 8601 UTC
  - action: "create_case"
  - result: "success"
  - metadata_json: {case_id: "...", espocrm_id: "...", assigned_to: "agent_name"}
  - error_msg: null
- **AND** log JSON: {"user_id": "...", "tool": "escalar", "result": "success", "case_id": "..."}

#### Scenario: Escalation logged on failure
- **WHEN** `escalar_a_humano()` falla (EspoCRM down, timeout, etc.)
- **THEN** audit table registra:
  - result: "failed"
  - error_msg: "EspoCRM API timeout" (short message, NO stack trace)
  - metadata_json: {retry_count: 3, last_error_code: 504}

### Requirement: Agendar Cita Audit
El sistema SHALL loguear cada invocación de `agendar_cita()`.

#### Scenario: Appointment logged on success
- **WHEN** usuario invoca "Agendar una consultoría" → tool `agendar_cita()` ejecuta exitosamente
- **THEN** audit table registra:
  - user_id, user_phone, tool_name: "agendar_cita"
  - timestamp: ISO 8601 UTC
  - action: "schedule_event"
  - result: "success"
  - metadata_json: {event_id: "Google Calendar event ID", event_datetime: "2026-07-14T14:30:00Z", attendees: ["user", "support"]}
  - error_msg: null

#### Scenario: Appointment logged on failure
- **WHEN** `agendar_cita()` falla (Google Calendar API error)
- **THEN** audit table registra:
  - result: "failed"
  - error_msg: "Google Calendar quota exceeded"

### Requirement: Consultar Licencia Audit
El sistema SHALL loguear cada invocación de `consultar_licencia()`.

#### Scenario: License check logged
- **WHEN** usuario invoca "¿Hasta cuándo tengo soporte?" → tool `consultar_licencia()` ejecuta
- **THEN** audit table registra:
  - user_id, user_phone, tool_name: "consultar_licencia"
  - timestamp: ISO 8601 UTC
  - action: "check_license"
  - result: "valid" | "expired" | "not_found"
  - metadata_json: {license_type: "premium", expiry_date: "2026-12-31", status: "active"}
  - error_msg: null si success, o error message si falló

### Requirement: Reclasificar Caso Audit
El sistema SHALL loguear cada invocación de `reclasificar_caso_sin_licencia()`.

#### Scenario: Case reclassification logged
- **WHEN** soporte reclasifica caso de "Técnico" a "Comercial" → tool `reclasificar_caso_sin_licencia()` ejecuta
- **THEN** audit table registra:
  - user_id: Soporte agent ID
  - user_phone: null (internal operation)
  - tool_name: "reclasificar_caso_sin_licencia"
  - timestamp: ISO 8601 UTC
  - action: "reclassify_case"
  - result: "success" | "failed"
  - metadata_json: {case_id: "...", old_category: "Técnico", new_category: "Comercial", reason: "..."}

### Requirement: Async Audit Writing
El sistema SHALL usar queue async para escribir audit logs sin bloquear herramientas.

#### Scenario: Tool returns fast despite slow DB
- **WHEN** database lento (>500ms latency)
- **THEN** tool retorna resultado a usuario en <100ms
- **AND** audit log queued para escritura async
- **AND** worker background escribe a DB sin bloquear

#### Scenario: Audit retention
- **WHEN** audit log tiene >90 días de antigüedad
- **THEN** puede ser archivado/borrado (compliance: 90 días mínimo)

### Requirement: Audit Log Security
Audit logs NUNCA SHALL contener: API keys, OAuth tokens, passwords, stack traces completos.

#### Scenario: Sensitive data scrubbed
- **WHEN** error_msg registra excepción
- **THEN** mensaje es short (ej: "Google API timeout") SIN token o credential
- **AND** metadata_json NO incluye respuestas completas de API (solo valores relevantes)
