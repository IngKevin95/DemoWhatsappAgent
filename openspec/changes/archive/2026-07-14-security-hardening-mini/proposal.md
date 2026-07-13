# Propuesta: Security Hardening — MINI (v1.0)

## Why

Demo WhatsApp bot actualmente vulnerable a ataques DDoS básicos, input injection, y falta de auditoría de decisiones críticas. v1.0 requiere protección mínima demostrable (rate limiting, input validation) + audit trail de escala/agendar/licencia para confiabilidad y cumplimiento básico.

## What Changes

- **Rate Limiting**: Webhook protegido con límite 10 req/min/IP; requests excedentes retornan 429
- **Input Validation**: Sanitización de payload usuario (remove SQL, script tags, peligrosos); antes de Gemini
- **Audit Logging**: Todas las decisiones críticas (escalar, agendar, consultar licencia, reclasificar) quedan registradas en tabla audit_logs con user_id, tool, timestamp, result
- **Secrets Scrubbing**: Tokens (DATABASE_URL, GOOGLE_*, META_*) jamás aparecen en logs, incluso en exceptions

## Capabilities

### New Capabilities

- `rate-limiting`: Middleware que limita requests por IP a 10 req/min; retorna 429 si se excede
- `input-validation`: Sanitización de input usuario (SQL injection, XSS removal) antes de procesar con Gemini
- `audit-logging`: Registro de decisiones críticas (escalar_a_humano, agendar_cita, consultar_licencia, reclasificar_caso) con user + timestamp + result
- `secrets-scrubbing`: Filter en logging que reemplaza tokens sensibles con ***REDACTED***; CI gate que bloquea secrets en logs

### Modified Capabilities

- `webhook-processing`: Ahora aplica rate limiting + input validation antes de procesar

## Impact

- **Code**: `main.py` (apply rate limit + input validation), `tools.py` (audit logging en 4 funciones), `agent/middleware/` (nuevos: rate_limiter.py, input_validator.py, secrets_filter en logging.py)
- **Database**: Nueva tabla `audit_logs` (migration script)
- **CI/CD**: Nuevo test `test_secrets_not_in_logs.py` en security gate
- **Dependencies**: Ninguna nueva (usa stdlib + PyBreaker/similar si ya existe)
- **Config**: `RATE_LIMIT_REQUESTS=10`, `RATE_LIMIT_WINDOW_SECONDS=60`, `INPUT_VALIDATION_ENABLED=true` en `.env`

## Trazabilidad

**Épica**: EP-003-MINI  
**Historias**:
- HU-030: Rate limiting webhook (4h)
- HU-031: Input validation (3h)
- HU-032: Audit logging (6h)
- HU-033: Secrets scrubbing (2h)

**Objetivo PRD**: Objetivo 3 (audit logging), Objetivo 4 (funcionar seguro 24/7)  
**KPIs**: Error rate <1%, Rate limiting enforced
