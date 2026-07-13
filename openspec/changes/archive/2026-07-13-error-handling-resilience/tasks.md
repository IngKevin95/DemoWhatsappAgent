# Tasks: Error Handling & Resilience - Desglose Ejecutable

## Phase 1: Testing (RED)

- [ ] Write tests for retry logic (`tests/unit/test_retry_logic.py`)
  - [ ] test_retry_succeeds_on_first_attempt
  - [ ] test_retry_succeeds_after_transient_failure
  - [ ] test_retry_exhausts_max_attempts
  - [ ] test_retry_exponential_backoff
  - [ ] test_retry_with_jitter
  - [ ] test_async_retry_succeeds_after_failure
  - [ ] test_retry_decorator_basic
  - [ ] test_retry_respects_specific_exceptions
  - [ ] Verify all tests FAIL (no code yet)

- [ ] Write tests for circuit breaker (`tests/unit/test_circuit_breaker.py`)
  - [ ] test_circuit_breaker_closed_allows_calls
  - [ ] test_circuit_opens_after_threshold_failures
  - [ ] test_circuit_open_fails_fast
  - [ ] test_circuit_half_open_on_timeout
  - [ ] test_circuit_half_open_success_closes
  - [ ] test_circuit_half_open_failure_reopens
  - [ ] test_circuit_breaker_metrics
  - [ ] Verify all tests FAIL

- [ ] Write tests for logging (`tests/unit/test_logging.py`)
  - [ ] test_json_output_format
  - [ ] test_secrets_scrubbed
  - [ ] test_trace_id_propagation
  - [ ] test_log_levels_respected
  - [ ] test_stack_trace_included_in_error
  - [ ] Verify all tests FAIL

- [ ] Write tests for audit logging (`tests/integration/test_audit_logging.py`)
  - [ ] test_audit_log_entry_created_on_success
  - [ ] test_audit_log_entry_created_on_failure
  - [ ] test_metadata_jsonb_correct
  - [ ] test_timestamp_assigned
  - [ ] test_query_by_user_phone
  - [ ] test_transaction_rollback_preserves_audit
  - [ ] Verify all tests FAIL

- [ ] Write tests for fallback responses (`tests/unit/test_fallback_responses.py`)
  - [ ] test_fallback_gemini_timeout
  - [ ] test_fallback_google_calendar_down
  - [ ] test_fallback_espocrm_error
  - [ ] test_fallback_firebird_unavailable
  - [ ] test_fallback_logged
  - [ ] Verify all tests FAIL

## Phase 2: Implementation (GREEN)

- [ ] Implement retry logic (`agent/middleware/retry.py`)
  - [ ] retry_operation() function (sync + async)
  - [ ] @retry decorator
  - [ ] Exponential backoff calculation
  - [ ] Jitter ±20%
  - [ ] Retryable exceptions filtering
  - [ ] Run tests: ALL PASS

- [ ] Implement circuit breaker (`agent/middleware/circuit_breaker.py`)
  - [ ] CircuitBreaker class (Pybreaker wrapper)
  - [ ] States: CLOSED, OPEN, HALF_OPEN
  - [ ] Threshold & timeout configuration
  - [ ] CircuitBreakerOpen exception
  - [ ] Metrics/state tracking
  - [ ] Run tests: ALL PASS

- [ ] Implement logging (`agent/middleware/logging.py`)
  - [ ] setup_structured_logging() function
  - [ ] JSON formatter
  - [ ] Secrets scrubber (regex patterns)
  - [ ] trace_id contextvars helper
  - [ ] Integration with logging module
  - [ ] Run tests: ALL PASS

- [ ] Implement audit logging (`agent/middleware/audit_logger.py`)
  - [ ] Database migration: `audit_log` table creation
  - [ ] AuditLogger class
  - [ ] @audit_log decorator
  - [ ] log_success() & log_failure() methods
  - [ ] Metadata JSONB handling
  - [ ] Run tests: ALL PASS

- [ ] Implement fallback responses (`agent/middleware/fallback.py`)
  - [ ] FALLBACK_RESPONSES dict (5 servicios)
  - [ ] get_fallback(service, error_type) function
  - [ ] Logging on fallback use
  - [ ] Run tests: ALL PASS

## Phase 3: Integration (GREEN + Refactor)

- [ ] Update `agent/brain.py`
  - [ ] Import retry, circuit_breaker, fallback
  - [ ] Wrap Gemini call: `@breaker_gemini + timeout 3s → fallback`
  - [ ] Update structured logging calls
  - [ ] Run tests: ALL PASS

- [ ] Update `agent/integrations/google.py`
  - [ ] Import retry, circuit_breaker
  - [ ] Wrap crear_evento_calendar: `@breaker_google + @retry`
  - [ ] Wrap enviar_email: `@breaker_gmail + @retry`
  - [ ] Wrap horarios_libres: `@breaker_google + @retry`
  - [ ] Run tests: ALL PASS

- [ ] Update `agent/integrations/espocrm.py`
  - [ ] Import retry, circuit_breaker
  - [ ] Wrap API calls: `@breaker_crm + @retry`
  - [ ] Run tests: ALL PASS

- [ ] Update `agent/tools.py`
  - [ ] Import audit_logger, fallback
  - [ ] escalar_a_humano: `@audit_log + breaker_crm + breaker_gmail + fallback`
  - [ ] agendar_cita: `@audit_log + breaker_google + fallback`
  - [ ] reclasificar_caso: `@audit_log + local DB update (no retry)`
  - [ ] consultar_licencia: `@audit_log + breaker_fb + retry`
  - [ ] Run tests: ALL PASS

- [ ] Update `agent/memory.py`
  - [ ] Import retry
  - [ ] Wrap Postgres queries: `@retry(max_attempts=2, base_delay=0.1)`
  - [ ] Run tests: ALL PASS

- [ ] Update `agent/main.py`
  - [ ] setup_structured_logging() at app startup
  - [ ] Set trace_id in webhook handler (contextvars)
  - [ ] Pass trace_id to brain.py & tools.py
  - [ ] Run tests: ALL PASS

- [ ] Refactor for simplicity (ponytail)
  - [ ] Remove duplicate retry logic from brain.py (fix/gemini-429)
  - [ ] Check for duplicated Meta wrapper + email try-catch
  - [ ] Ensure <30L functions (escalar_a_humano, agendar_cita)
  - [ ] Run tests: ALL PASS

## Phase 4: Verification (End-to-End)

- [ ] Run full test suite
  - [ ] `pytest tests/ -v --cov=agent --cov-report=term-missing`
  - [ ] Coverage >80% for middleware/, >60% overall
  - [ ] All tests GREEN

- [ ] Smoke test: journey end-to-end
  - [ ] Start app locally
  - [ ] Simulate webhook: "quiero saber precio de Módulo X"
  - [ ] Verify: response + logs JSON + no secrets visible
  - [ ] Simulate error: break EspoCRM mock
  - [ ] Verify: fallback response + circuit open + audit log
  - [ ] Simulate recovery: restore EspoCRM mock
  - [ ] Verify: circuit closed + retry success + audit log
  - [ ] Check: no stack traces in output, only fallback

- [ ] Lint & type check
  - [ ] `ruff check agent/ tests/`
  - [ ] `mypy agent/ --ignore-missing-imports` (if applicable)
  - [ ] All GREEN

- [ ] Security check
  - [ ] No hardcoded credentials in code
  - [ ] Secrets scrubber tested (DATABASE_URL, GOOGLE_*, META_*, FIREBIRD_*)
  - [ ] No PII in logs (phone numbers masked)
  - [ ] Audit table access controlled (if future)

## Dependencies

- [ ] Add `pybreaker~=1.4.0` to requirements.txt
- [ ] Run `pip install -e .` to verify

## Documentation (auto-generated from specs)

- [ ] All specs linked from proposal.md
- [ ] README.md updated with error handling section (optional)

## Acceptance Criteria (AC from HU-019)

### AC-1: Cambiar Categoría
- [ ] `reclasificar_caso_sin_licencia()` updates DB
- [ ] Audit log registra: quién, qué, cuándo, resultado anterior
- [ ] Test: AC-1 pasa en verde

### AC-2: Caso No Existe
- [ ] Función retorna error message claro
- [ ] No stacktrace al usuario
- [ ] Audit log registra error
- [ ] Test: AC-2 pasa en verde

### AC-3: Caso Ya Reclasificado
- [ ] Función detecta estado previo
- [ ] Ofrece opción reversa
- [ ] Audit log de reversals
- [ ] Test: AC-3 pasa en verde

## Notes

- Order matters: RED (all tests fail) → GREEN (all tests pass) → REFACTOR
- Never skip TDD cycle
- Refactor ONLY after all tests green
- No production code before failing test
- Each task can run independently (after Phase 1 complete)
