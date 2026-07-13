# Specification: Input Validation

Sanitizar entrada de usuario antes de procesar con Gemini, removiendo o escapando payloads peligrosos (SQL injection, XSS, scripts).

## ADDED Requirements

### Requirement: SQL Injection Prevention
El sistema SHALL detectar y neutralizar intentos de SQL injection removiendo keywords y caracteres peligrosos.

#### Scenario: SQL injection payload blocked
- **WHEN** usuario envía mensaje: `'; DROP TABLE cases; --`
- **THEN** sanitizer detecta SQL keywords (DROP, DELETE, INSERT, etc.) y caracteres peligrosos (`;`, `--`)
- **AND** payload transformado a: `DROP TABLE cases` (sin caracteres especiales)
- **AND** Gemini recibe texto limpio: `DROP TABLE cases`
- **AND** sistema loguea: {original_input (redacted), sanitized_input, action="sql_injection_detected"}

#### Scenario: Legitimate SQL keywords in context allowed
- **WHEN** usuario envía: `SELECT * FROM public_documentation` o `WHERE can I find pricing?`
- **THEN** sanitizer distingue contexto (keyword lowercase o en oración, no SQL statement)
- **AND** mensaje pasa sin cambio
- **AND** procesamiento normal continúa
- **AND** sistema loguea: {message_allowed, potential_false_positive=true, reason="valid_context"}

### Requirement: XSS Prevention
El sistema SHALL detectar y remover HTML tags y script payloads.

#### Scenario: Script tag blocked
- **WHEN** usuario envía: `<script>alert('xss')</script>`
- **THEN** sanitizer detecta HTML tags (`<`, `>`) y script keywords
- **AND** payload transformado a: `scriptalertxssscript` (tags removidos)
- **AND** Gemini recibe: `scriptalertxssscript`
- **AND** sistema loguea: {xss_attempt_detected, sanitized_output}

#### Scenario: Angle brackets in non-tag context allowed
- **WHEN** usuario envía: `Use <name> format` o `Send to <email@example.com>`
- **THEN** sanitizer distingue: `<script>` (tag peligroso) vs `<name>` (contexto legítimo)
- **AND** mensaje pasa sin cambio (allow angle brackets si no son HTML tag)
- **AND** procesamiento normal

### Requirement: Input Validation Coverage
Input validation SHALL aplicar en todos los entry points de usuario (webhook + internos).

#### Scenario: Webhook message sanitized
- **WHEN** webhook recibe request de Meta con texto de usuario
- **THEN** input validator corre DESPUÉS de rate limiting, ANTES de enviar a Gemini
- **AND** mensaje sanitizado antes de cualquier procesamiento

#### Scenario: Tool arguments validated
- **WHEN** Gemini llama a tool (ej: `agendar_cita(fecha="2026-07-14", descripcion="<img>test")`)
- **THEN** descripción sanitizada antes de usar en Google Calendar API

### Requirement: Input Validation Logging
Todos los eventos de validación SHALL loguear en formato JSON: original_input (redacted), sanitized_input, action, reason.

#### Scenario: Validation log entry
- **WHEN** payload es detectado y sanitizado
- **THEN** log contiene: {"original_input": "***REDACTED***", "sanitized_input": "cleaned text", "action": "sql_injection_detected", "reason": "DROP keyword found"}
- **AND** timestamp ISO 8601 UTC

### Requirement: Configuration
Input validation SHALL poder activarse/desactivarse vía .env.

#### Scenario: Config toggle
- **WHEN** .env contiene INPUT_VALIDATION_ENABLED=true
- **THEN** input validator activo
- **WHEN** INPUT_VALIDATION_ENABLED=false
- **THEN** input validator desactivado (pass-through)
