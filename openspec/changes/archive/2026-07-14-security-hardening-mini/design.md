# Diseño: Security Hardening — MINI

## Context

DemoWhatsappAgent webhook actualmente acepta todos los requests sin protección. v1.0 requiere:
1. Defensa contra DDoS básico (rate limiting por IP)
2. Sanitización de input usuario (remove SQL injection, XSS)
3. Auditoría de decisiones críticas (quién escaló, cuándo, resultado)
4. Protección de secretos en logs (nunca exponer tokens)

Flujo webhook hoy: Meta signature validation → Gemini intent → tools → response. Insertar security en: (1) post-validation, pre-processing, (2) per-tool execution, (3) logging pipeline.

## Goals / Non-Goals

**Goals:**
- Bloquear >10 req/min/IP (429 response; log event)
- Sanitizar input usuario antes de enviar a Gemini (remove SQL, scripts, peligrosos)
- Registrar todas las decisiones críticas (escalar, agendar, consultar licencia, reclasificar) en audit table
- Scrubbing automático de secrets (DATABASE_URL, GOOGLE_*, META_*) en logs
- Pass security tests + CI gate que bloquea secrets en logs

**Non-Goals:**
- Encryption at rest (DB already local)
- mTLS entre servicios (monolítica, no aplica)
- Rate limiting multi-tier (per-user, per-endpoint) — solo per-IP v1.0
- Full compliance audit (SOC2, GDPR) — mínimo v1.0

## Decisions

### 1. Rate Limiting: Sliding Window Algorithm + In-Memory Store

**Decision**: Sliding window (simple, suficiente v1.0) en memoria con dict `{ip: [timestamps]}`

**Rationale**: 
- Demo de corta vida → no necesita persistencia Redis
- O(n) lookup aceptable para <100 IPs concurrentes
- Reset automático por timestamp (1 minuto)

**Alternatives**:
- Token bucket: más preciso, overhead innecesario v1.0
- Redis: overkill, agrega dependencia, complejidad deployment
- Database: latency inaceptable en middleware

**Implementation**:
- Middleware en `agent/middleware/rate_limiter.py`
- Clase `RateLimiter` con método `is_allowed(ip: str) → bool`
- Config: `RATE_LIMIT_REQUESTS=10`, `RATE_LIMIT_WINDOW_SECONDS=60` en `.env`
- X-Forwarded-For header (CDN/proxy): extrae client_ip correcto
- Log: JSON con `{source_ip, requests_count, action="rate_limited", timestamp}`

### 2. Input Validation: Whitelist + Blacklist Hybrid

**Decision**: Whitelist-first (allow safe chars) + blacklist (block known dangerous patterns)

**Rationale**:
- Whitelist → fewer false negatives (catch more attacks)
- Blacklist exception → allow legitimate edge cases (SELECT in documentation, <name> in angle brackets)
- Log both original (redacted) + sanitized for audit

**Alternatives**:
- Pure blacklist: high false positives (SELECT in normal messages blocked)
- Pure whitelist: too restrictive (valid messages rejected)
- ML classifier: overkill, unreliable v1.0

**Implementation**:
- Middleware en `agent/middleware/input_validator.py`
- Función `sanitize(text: str) → str`
- Whitelist: alphanumeric + spaces + safe punctuation (`.`, `,`, `?`, `!`, `-`, `'`, `"`)
- Blacklist exceptions: `SELECT`, `WHERE`, `INSERT`, etc. in all-caps = SQL keyword context (allow lowercase or mixed case)
- Script tag removal: `<script>`, `<iframe>`, etc. stripped
- Log: `{original_input (redacted), sanitized_input, action="sql_injection_detected"|"xss_detected"|"allowed"}`

### 3. Audit Logging: Async Write to `audit_logs` Table

**Decision**: Async queue + background writer (don't block tool on slow DB)

**Rationale**:
- Tools must return fast (Gemini latency already 1-2s)
- Blocking on DB write = user-facing latency + retry complexity
- Async → fire-and-forget reliability (queue survives short DB outages)

**Alternatives**:
- Sync write: latency penalty, customer experience hurt
- Syslog: loses structure, harder to query/analyze
- File-based: rotation complexity, no structured queries

**Implementation**:
- Table schema: `audit_logs(id, user_id, user_phone, tool_name, timestamp, action, result, metadata_json, error_msg, created_at)`
- Middleware en `agent/middleware/audit_logger.py`
- Queue (in-memory dict of deques per tool) + thread-safe async writer
- 90-day retention (compliance minimum)
- Never log: API keys, OAuth tokens, passwords, full stack traces
- Log fields: user_id, user_phone, tool_name, timestamp (ISO 8601 UTC), action (e.g., "create_case"), result ("success"/"failed"), metadata_json (case_id, event_id, etc.), error_msg (short, no traceback)
- 4 tools to audit: `escalar_a_humano`, `agendar_cita`, `consultar_licencia`, `reclasificar_caso_sin_licencia`

### 4. Secrets Scrubbing: Logging Filter Class + CI Gate

**Decision**: Centralized `SecretsFilter` in logging config + CI test that scans logs for leaks

**Rationale**:
- Single point of redaction = no scattered code
- Patterns stored centralized (easy to update)
- CI gate = automated prevention (human code review can't catch everything)
- Asyncio logging hook = no performance penalty

**Alternatives**:
- Exception handler per integration: verbose, easy to miss
- Structured logging with explicit fields: verbose, coupling to Gemini/EspoCRM
- Trust developers: human error, happened already (GAP-EP002-3)

**Implementation**:
- Filter class en `agent/middleware/logging.py`: `SecretsFilter`
- Patterns: `DATABASE_URL`, `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_OAUTH_TOKEN`, `access_token`, `META_API_TOKEN`, `ya29.*` (Google token), `AKIA.*` (AWS token)
- Replacement: `***REDACTED***` or `[REDACTED_<TYPE>]`
- Exception logging: catch exception, don't log `response.text` (log status_code only)
- CI test: `tests/security/test_secrets_not_in_logs.py`
  - Runs full test suite
  - Scans all `.log` files for patterns
  - Fails if any pattern found (blocks PR merge)

### 5. X-Forwarded-For Handling (CDN/Proxy)

**Decision**: Trust first IP in X-Forwarded-For chain (if header present); else use direct socket IP

**Rationale**:
- CDN/reverse proxy adds: `client_ip, proxy_ip, cdn_ip`
- First value = real client IP
- Direct socket IP = proxy/CDN IP (wrong rate limit counter)

**Alternatives**:
- Always use direct socket: misses proxy scenario
- Trust last IP: CDN could spoof

**Implementation**: Rate limiter extracts header or socket IP; logs both for audit

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Rate limiter memory grows unbounded (many IPs) | Reset old entries >5 min stale; max 1K IPs in memory; fallback: log-only if memory full |
| Input sanitization rejects legitimate customer messages (false positive) | Whitelist approach allows most; log both original + sanitized for auditor review; edge case fix v1.1 |
| Async audit queue loses events if process crashes | Accept loss (low-stakes audit v1.0); add flush-on-shutdown v1.1; switch to sync if audit becomes critical |
| Secrets filter false negatives (missed patterns) | CI gate catch most; manual code review second line; add new patterns as discovered |
| X-Forwarded-For spoofing (malicious proxy) | Trust model: assume internal proxy not spoofed; public cloud scenario requires mTLS v1.1 |

## Migration Plan

**Phase 1: Middleware deployment**
1. Add `agent/middleware/rate_limiter.py`, `input_validator.py`, `audit_logger.py`
2. Update `agent/middleware/logging.py` with `SecretsFilter`
3. Update `.env.example` with new config vars
4. Create migration: `migrate_audit_logs_table.py`

**Phase 2: Integration into webhook**
1. `main.py::recibir_webhook()`: apply rate limiter (post-signature validation)
2. Apply input validator (post-rate limit)
3. Create `audit_logs` table (run migration)

**Phase 3: Tool auditing**
1. Update `tools.py`: wrap 4 critical tools with audit logging
2. Test audit_logs writes + queries

**Phase 4: CI gate + testing**
1. Add `tests/security/test_secrets_not_in_logs.py`
2. Add `tests/security/test_rate_limiting.py`, `test_input_validation.py`
3. Configure GitHub Actions secret-scanning

**Rollback**: Remove middleware instantiation from `main.py`, remove migration (audit_logs table can stay)

## Open Questions

1. Should rate limit be per-webhook-endpoint (currently global)? → v1.0: global (simple). v1.1: per-endpoint if DDoS patterns suggest.
2. Should audit_logs include full Gemini response or just decision? → v1.0: decision + error only (short logs). v1.1: full response if storage allows.
3. How long to retain audit_logs? → v1.0: 90 days. v1.1: review based on compliance requirement.
