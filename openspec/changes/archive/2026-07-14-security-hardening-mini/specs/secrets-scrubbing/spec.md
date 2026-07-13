# Specification: Secrets Scrubbing

Garantizar que tokens de API, credenciales de base de datos y otras secrets NUNCA aparezcan en logs, ni siquiera en exception logs. Scrubbing automático de campos sensibles.

## ADDED Requirements

### Requirement: Database URL Redaction
El sistema SHALL redactar DATABASE_URL en todos los logs, incluso en exception handlers.

#### Scenario: Database connection error logged safely
- **WHEN** excepción en conexión a Postgres
- **THEN** log entry registra exception type, message, traceback
- **AND** DATABASE_URL value redactado como: `***REDACTED***`
- **AND** log muestra: `DATABASE_URL: ***REDACTED***` (NO `postgresql://user:pass@host:5432/db`)
- **AND** grep en logs por "postgresql://" retorna 0 matches

#### Scenario: Connection string in traceback scrubbed
- **WHEN** traceback de exception incluye connection string literal
- **THEN** todos los "postgresql://..." strings en traceback reemplazados con `***REDACTED***`

### Requirement: Google API Tokens Redaction
El sistema SHALL redactar GOOGLE_APPLICATION_CREDENTIALS, GOOGLE_OAUTH_TOKEN, access_token en logs.

#### Scenario: Google API exception logged safely
- **WHEN** excepción en Google Calendar API call
- **THEN** exception se loguea en `integrations/google.py`
- **AND** fields redactados: GOOGLE_APPLICATION_CREDENTIALS, GOOGLE_OAUTH_TOKEN, access_token
- **AND** log muestra: `GOOGLE_OAUTH_TOKEN: ***REDACTED***`
- **AND** HTTP Authorization header logged como: `Authorization: ***REDACTED***` (NO "Bearer ya29...")
- **AND** grep en logs por "ya29" (Google token prefix) retorna 0 matches

#### Scenario: Credential in request body scrubbed
- **WHEN** HTTP request body contiene credential
- **THEN** credential field redactado antes de loguear request

### Requirement: Meta API Token Redaction
El sistema SHALL redactar META_API_TOKEN en logs.

#### Scenario: Meta webhook signature validation error
- **WHEN** excepción en Meta webhook signature validation
- **THEN** META_API_TOKEN redactado como: `***REDACTED***`
- **AND** log muestra exception con token hidden
- **AND** grep en logs por patterns de token Meta (ej: "EAAx...") retorna 0 matches

### Requirement: Firebird Database Credentials Redaction
El sistema SHALL redactar FIREBIRD_* env vars (user, password, host).

#### Scenario: Firebird connection error
- **WHEN** excepción en conexión a Firebird
- **THEN** FIREBIRD_USER, FIREBIRD_PASSWORD, FIREBIRD_HOST redactados
- **AND** log muestra: `FIREBIRD_PASSWORD: ***REDACTED***`

### Requirement: CI/CD Gate Blocks Secret Leaks
El sistema SHALL bloquear PRs que contengan secrets en logs.

#### Scenario: CI test catches secret leak
- **WHEN** PR intenta mergear código con secrets en logs
- **THEN** CI test `test_secrets_not_in_logs.py` corre
- **AND** test scans todos los logs generados durante test suite
- **AND** test busca patterns: `postgresql://`, `ya29.*`, `AKIA.*`, `access_token=`, `firebird://`
- **AND** si patterns encontrados: test FALLA, PR bloqueado
- **AND** si test pasa: PR puede continuar

#### Scenario: CI gate is required status check
- **WHEN** branch requires status check para merge a main
- **THEN** `secrets-not-in-logs` es status check REQUIRED
- **AND** rama NO puede mergear si secrets gate falla

### Requirement: Centralized Secrets Filter
El sistema SHALL usar centralized `SecretsFilter` en logging config.

#### Scenario: Filter applied to all logs
- **WHEN** cualquier módulo loguea (incluso exception handlers)
- **THEN** todos los logs pasan por `SecretsFilter`
- **AND** filter intercepta y redacta secrets automáticamente
- **AND** sin necesidad de código manual per-module

#### Scenario: Custom patterns updatable
- **WHEN** nuevo secret pattern identificado
- **THEN** agregado a patrón list centralizado (NO esparcido en múltiples archivos)
- **AND** siguiente log redacta automáticamente

### Requirement: Exception Logging Best Practices
El sistema SHALL loguear exceptions sin exponer response bodies completos.

#### Scenario: Exception details safe
- **WHEN** try/except en integrations/google.py
- **THEN** except block: NO loguear `response.text` completo
- **AND** SÍ loguear: `response.status_code`, `response.headers.get('error')` (si safe)
- **AND** short error message solamente (ej: "Google API timeout")

#### Scenario: Stack trace redacted
- **WHEN** exception loguea full stack trace
- **THEN** URLs en stack trace contienen credentials redactadas
- **AND** variable values en locals() redactados si contienen secrets
