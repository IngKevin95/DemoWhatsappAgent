# Proposal: Error Handling & Resilience

## Por Qué

**Riesgos identificados en PRD:**
- Gemini latency, Google unavailable, EspoCRM auth, Firebird down, rate attacks
- Profundidad de flujos (e.g., `reclasificar_caso_sin_licencia` tiene 7 nodos) → cambio en un punto puede cascadear
- Error rate target es <1%, hoy = desconocido (sin monitoring)
- Soporte no confía en el bot si escala falla silenciosamente

**Blocker actual:**
- Retry logic inconsistente (fix/gemini-429 es manual, no sistemático)
- Sin circuit breakers (fail-open si servicios degradados)
- Sin audit logging (no trazabilidad en high-stakes tools)
- Fallback response inexistente si Gemini times out

## Qué Cambia

### Antes
- `escalar_a_humano()` falla si EspoCRM/Gmail timeout → error silencioso
- `agendar_cita()` no reintenta si Google Calendar temporary error
- `reclasificar_caso_sin_licencia()` no registra auditoría
- Retry spread across tools.py + brain.py (duplicado, inconsistente)

### Después
- Retry con exponential backoff + jitter (aplicado uniformemente)
- Circuit breakers para Google APIs, EspoCRM, Firebird
- JSON structured logging (levels: DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Fallback response si Gemini times out (frase pre-grabada)
- Audit logging para tools de alto riesgo (escalar, agendar, reclasificar, consultar_licencia)

## Capacidades Incluidas

1. **Retry Logic**
   - Decorator `@retry(max_attempts=3, base_delay=1, backoff=2)` en `agent/middleware/retry.py`
   - Aplica a: Google API calls, EspoCRM API calls, Firebird queries
   - Exponential backoff: 1s, 2s, 4s (máx 16s)
   - Jitter ±20% para evitar thundering herd

2. **Circuit Breaker**
   - `agent/middleware/circuit_breaker.py` usando Pybreaker
   - Estados: CLOSED (normal), OPEN (fail-fast), HALF_OPEN (test recovery)
   - Thresholds: 5 failures en 60s → OPEN; después 30s → HALF_OPEN; 1 success → CLOSED
   - Servicios cubiertos: Google, EspoCRM, Firebird, Gemini

3. **Logging Estructurado**
   - `agent/middleware/logging.py`: JSON output (timestamp, level, service, message, trace_id)
   - Levels: DEBUG (Postgres queries), INFO (tool calls), WARNING (retry triggered), ERROR (circuit open), CRITICAL (service down)
   - Secrets scrubber: DATABASE_URL, GOOGLE_*, META_*, FIREBIRD_* nunca en logs

4. **Fallback Responses**
   - Si Gemini times out después de 3 retries: devolver "Disculpa, estoy un poco lento. Intenta de nuevo en unos segundos."
   - Si EspoCRM está down: "No puedo acceder al sistema de soporte ahora. Un agente te llamará pronto."
   - Si Firebird down: "Sistema de licencias no disponible. Verificaré tu estado más tarde."

5. **Audit Logging**
   - `agent/middleware/audit_logger.py`: inserta en tabla `audit_log` (Postgres)
   - Campos: user_phone, tool_name, action, result, timestamp, metadata
   - High-stakes tools: `escalar_a_humano`, `agendar_cita`, `reclasificar_caso_sin_licencia`, `consultar_licencia`

## Cómo se Mide Éxito

| Métrica | Target | Método |
|---------|--------|--------|
| Error rate en API | <1% | Prometheus metrics |
| P99 latency (Gemini call) | <3s | APM instrumentation |
| Retry success rate | ≥80% | Logs analysis |
| Circuit breaker trips | ≤5/día (bajo tráfico demo) | Logs + alertas |
| Audit logging coverage | 100% (high-stakes tools) | Code review + tests |
| Tests de error handling | ≥10 AC | TDD |

## Trazabilidad

**Épica:** EP-002 (Error Handling & Resilience)  
**Historias:** HU-019 (Reclasificación de Caso — incluye AC para audit)  
**Alcance:** Refactor + nuevas capas middleware (retry, circuit breaker, logging, audit)

**Artefactos generados:**
- `agent/middleware/retry.py` (decorator + exponential backoff)
- `agent/middleware/circuit_breaker.py` (Pybreaker wrapper)
- `agent/middleware/logging.py` (JSON + secrets scrubber)
- `agent/middleware/audit_logger.py` (Postgres audit trail)
- Updated `integrations/google.py`, `integrations/espocrm.py`, `tools.py` (usar decorators)
- Tests: `tests/test_retry_logic.py`, `test_circuit_breaker.py`, `test_audit_logging.py`, `test_fallback_responses.py`

## Impacto

- **Confiabilidad:** Error handling graciosa → mejora uptime y UX
- **Observability:** Audit logging + structured logs → debugging más rápido
- **Recuperación:** Circuit breakers + retry → menos cascadas
- **Cumplimiento:** Audit trail para escalar/agendar → compliance v1.0

## No Incluido (Diferido)

- Full encryption at rest para chat history (vira a EP-003)
- Rate limiting exhaustivo (vira a EP-003)
- Multi-region failover (vira a v1.1)
