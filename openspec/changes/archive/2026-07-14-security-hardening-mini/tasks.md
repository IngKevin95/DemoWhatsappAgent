# Tasks: Security Hardening — MINI

## 1. Middleware Infrastructure Setup

- [ ] 1.1 Create `agent/middleware/rate_limiter.py` with `RateLimiter` class
- [ ] 1.2 Create `agent/middleware/input_validator.py` with `sanitize()` function
- [ ] 1.3 Create `agent/middleware/audit_logger.py` with async queue writer
- [ ] 1.4 Update `agent/middleware/logging.py` to add `SecretsFilter` class
- [ ] 1.5 Add `.env.example` config vars: RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS, INPUT_VALIDATION_ENABLED

## 2. Database: Audit Logging Table

- [ ] 2.1 Create migration script: `migrations/create_audit_logs_table.py`
- [ ] 2.2 Run migration: `audit_logs` table exists in Postgres
- [ ] 2.3 Create indexes on (user_id, tool_name, timestamp) for query performance
- [ ] 2.4 Verify table schema matches spec: id, user_id, user_phone, tool_name, timestamp, action, result, metadata_json, error_msg, created_at

## 3. Rate Limiting Implementation (HU-030)

- [ ] 3.1 Implement sliding window algorithm in `RateLimiter` class
- [ ] 3.2 Handle X-Forwarded-For header extraction (CDN/proxy scenario)
- [ ] 3.3 Apply rate limiter middleware in `main.py::recibir_webhook()` post-signature validation
- [ ] 3.4 Return HTTP 429 with message "Too many requests. Límite: 10 req/min por IP" when limit exceeded
- [ ] 3.5 JSON logging format: {source_ip, requests_count, action, timestamp}
- [ ] 3.6 Test rate limit reset after 60 seconds
- [ ] 3.7 Test independent IP counters (IP-A limit doesn't affect IP-B)

## 4. Input Validation Implementation (HU-031)

- [ ] 4.1 Implement whitelist-first sanitizer in `input_validator.py`
- [ ] 4.2 Add blacklist patterns: SQL keywords (DROP, DELETE, INSERT, etc.), dangerous chars (`;`, `--`, `<script>`)
- [ ] 4.3 Implement whitelist exception logic (allow SELECT in lowercase, allow angle brackets if not HTML tag)
- [ ] 4.4 Apply input validator in `main.py::recibir_webhook()` post-rate-limit
- [ ] 4.5 JSON logging: {original_input (redacted), sanitized_input, action, reason}
- [ ] 4.6 Test SQL injection payload detection + neutralization
- [ ] 4.7 Test XSS payload detection + tag removal
- [ ] 4.8 Test legitimate messages pass through unchanged

## 5. Audit Logging Implementation (HU-032)

- [ ] 5.1 Implement async queue writer in `audit_logger.py`
- [ ] 5.2 Create background thread to flush queue → `audit_logs` table
- [ ] 5.3 Wrap `tools.py::escalar_a_humano()` with audit logging decorator
  - [ ] 5.3a Log: user_id, user_phone, tool="escalar_a_humano", action="create_case", result, case_id, error_msg
- [ ] 5.4 Wrap `tools.py::agendar_cita()` with audit logging
  - [ ] 5.4a Log: user_id, user_phone, tool="agendar_cita", action="schedule_event", result, event_id, event_datetime
- [ ] 5.5 Wrap `tools.py::consultar_licencia()` with audit logging
  - [ ] 5.5a Log: user_id, user_phone, tool="consultar_licencia", action="check_license", result, license_status
- [ ] 5.6 Wrap `tools.py::reclasificar_caso_sin_licencia()` with audit logging
  - [ ] 5.6a Log: user_id, tool="reclasificar_caso_sin_licencia", action="reclassify_case", case_id, old_category, new_category
- [ ] 5.7 Test async writes complete without blocking tool response
- [ ] 5.8 Verify all 4 tools log to `audit_logs` table correctly

## 6. Secrets Scrubbing Implementation (HU-033)

- [ ] 6.1 Implement `SecretsFilter` class in `agent/middleware/logging.py`
- [ ] 6.2 Add patterns: DATABASE_URL, GOOGLE_*, META_*, FIREBIRD_*, access_token, password, api_key
- [ ] 6.3 Register filter with Python logging framework (all handlers inherit filter)
- [ ] 6.4 Test DATABASE_URL redaction in exception logs
- [ ] 6.5 Test GOOGLE_OAUTH_TOKEN redaction (grep "ya29" returns 0)
- [ ] 6.6 Test META_API_TOKEN redaction
- [ ] 6.7 Test FIREBIRD_* credentials redaction
- [ ] 6.8 Update exception handlers in `integrations/google.py`, `integrations/espocrm.py`, `agent/db.py`
  - [ ] 6.8a Exception logging: NO `response.text` completo, solo status_code + short error
  - [ ] 6.8b Variables en traceback redactadas

## 7. Testing & CI Integration

- [ ] 7.1 Create `tests/security/test_rate_limiting.py`
  - [ ] 7.1a Test: 10 requests pass, 11th blocked with 429
  - [ ] 7.1b Test: Rate limit resets after 60s
  - [ ] 7.1c Test: IP-A limit ≠ IP-B limit
  - [ ] 7.1d Test: X-Forwarded-For handling
- [ ] 7.2 Create `tests/security/test_input_validation.py`
  - [ ] 7.2a Test: SQL injection payload neutralized
  - [ ] 7.2b Test: XSS payload neutralized
  - [ ] 7.2c Test: Legitimate messages pass
  - [ ] 7.2d Test: False positives handled (SELECT in documentation, <name> in context)
- [ ] 7.3 Create `tests/security/test_audit_logging.py`
  - [ ] 7.3a Test: `escalar_a_humano()` logged
  - [ ] 7.3b Test: `agendar_cita()` logged
  - [ ] 7.3c Test: `consultar_licencia()` logged
  - [ ] 7.3d Test: `reclasificar_caso_sin_licencia()` logged
  - [ ] 7.3e Test: Async writes complete (query audit_logs)
- [ ] 7.4 Create `tests/security/test_secrets_not_in_logs.py`
  - [ ] 7.4a CI gate: scan logs for DATABASE_URL pattern
  - [ ] 7.4b CI gate: scan logs for "ya29" (Google token)
  - [ ] 7.4c CI gate: scan logs for "AKIA" (AWS token)
  - [ ] 7.4d CI gate: FAIL if any pattern found
- [ ] 7.5 Add security tests to GitHub Actions workflow (`.github/workflows/test.yml`)
- [ ] 7.6 Run all tests locally: pytest -v tests/security/
- [ ] 7.7 Verify CI gate blocks PRs with secrets in logs

## 8. Integration & Validation

- [ ] 8.1 Webhook smoke test: send 15 requests in 60s, verify 11-15 return 429
- [ ] 8.2 Webhook smoke test: send SQL injection payload, verify sanitized
- [ ] 8.3 Webhook smoke test: trigger escalation, verify audit_logs entry
- [ ] 8.4 Webhook smoke test: verify logs contain NO DATABASE_URL, GOOGLE_*, META_*
- [ ] 8.5 Load test rate limiter: 100 concurrent IPs, verify independent counters
- [ ] 8.6 Performance check: audit logging + secrets filtering <100ms overhead per request

## 9. Documentation & Deployment

- [ ] 9.1 Update `ARCHITECTURE.md`: add Security section explaining rate limiting, audit logging, secrets scrubbing
- [ ] 9.2 Create runbook: "If rate limit fails: enable fallback in NocoDB"
- [ ] 9.3 Create runbook: "Audit logs queries: SELECT * FROM audit_logs WHERE tool_name=X AND timestamp > Y"
- [ ] 9.4 Update `.env.example` with all security config vars
- [ ] 9.5 Code review: All 4 middleware files + integration points in tools.py
- [ ] 9.6 Deployment: Tag release v1.0 with security changes
- [ ] 9.7 Post-deployment: Verify audit_logs table receiving data in staging

## Estimate

- **Rate Limiting (HU-030)**: 4h
- **Input Validation (HU-031)**: 3h
- **Audit Logging (HU-032)**: 6h
- **Secrets Scrubbing (HU-033)**: 2h
- **Testing & CI**: 4h
- **Integration & runbooks**: 2h
- **Total**: ~15h (~2 days backend + QA)
