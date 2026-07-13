# Design: Error Handling & Resilience - Decisiones Técnicas

## Arquitectura

```
webhook (main.py)
├── brain.py (generar_respuesta)
│   ├── [breaker_gemini] → retry → Gemini API
│   │   └── timeout 3s → fallback "estoy lento"
│   └── tools invocadas por LLM
├── tools.py
│   ├── escalar_a_humano
│   │   ├── [breaker_crm] → retry → EspoCRM.create_case
│   │   ├── [breaker_gmail] → retry → Gmail.send
│   │   └── audit_log (success/failure)
│   ├── agendar_cita
│   │   ├── [breaker_google] → retry → Google Calendar
│   │   ├── Meta.send_whatsapp
│   │   └── audit_log
│   ├── reclasificar_caso (HU-019)
│   │   ├── DB update (local, no retry)
│   │   ├── notify Comercial team
│   │   └── audit_log
│   ├── consultar_licencia
│   │   ├── [breaker_fb] → retry → Firebird query
│   │   └── audit_log
│   └── ... (otras sin cambios en v1.0)
└── memoria.py (Postgres)
    └── [retry] → query (2 intentos, delay 0.1s)

Middleware layer (nuevo):
├── retry.py: decorator + exponential backoff
├── circuit_breaker.py: Pybreaker wrapper
├── logging.py: JSON + secrets scrubber
├── audit_logger.py: audit_log table inserts
└── fallback.py: respuestas pre-grabadas
```

## Decisiones Clave

### 1. Retry con Exponential Backoff (no jitter en v1.0 por simplicidad)

**Alternativa rechazada:** Linear backoff (1s, 1s, 1s)
- Razón del rechazo: cascadas igual en thundering herd
- Elección: Exponential (1s, 2s, 4s) + jitter ±20%

**Alternativa rechazada:** Sin retry (solo circuit breaker)
- Razón del rechazo: transientes reales (connection pooling, GC pauses) serían fallos
- Elección: Retry ANTES de circuit (retry recupera transientes)

### 2. Circuit Breaker (Pybreaker, no custom implementation)

**Alternativa rechazada:** Implementar desde cero
- Razón: Pybreaker está probado, <50 LOC de overhead
- Elección: Usar Pybreaker + wrapper minimal

**Alternativa rechazada:** Sin circuit breaker
- Razón: Cascadas exponenciales si servicio está degradado
- Elección: Circuit breaker es obligatorio para fail-fast

### 3. Logging Estructurado JSON vs Regex-parseable text

**Alternativa rechazada:** Text logs + grep manual
- Razón: correlación imposible, debugging lento
- Elección: JSON + trace_id para ELK/Datadog future

### 4. Audit Trail en DB vs Logs

**Alternativa rechazada:** Solo logs
- Razón: compliance/support queries necesitan structured access
- Elección: Audit table (INSERT-only, queryable)

### 5. Fallback Strategy (graceful degradation)

**Alternativa rechazada:** Error inmediato
- Razón: UX pésima (usuario piensa bot broke)
- Elección: Fallback honestos ("pronto te llamo") en timeout

**Alternativa rechazada:** Retry infinito
- Razón: latencia inaceptable
- Elección: Timeout 3s + fallback

## Layers Tocadas

| Layer | Cambios | Impacto | Riesgo |
|-------|---------|--------|--------|
| middleware (nueva) | retry, CB, logging, audit | Toda stack | bajo (aislado) |
| brain.py | @breaker + timeout fallback en genai call | generar_respuesta | bajo |
| tools.py | @retry/@breaker en tools + audit | 4 funciones | bajo |
| integrations/ | usar decorators | Google, EspoCRM, Firebird | bajo |
| db.py | sin cambios | — | N/A |
| memory.py | @retry en queries | Postgres access | bajo |
| main.py | setup logging al start | Boot | bajo |

## Dependencias Nuevas

```
Pybreaker ~1.4.0  # Circuit breaker
# No hay más (retry/logging/audit son stdlib + Postgres)
```

**Justificación:** Pybreaker es <50KB, battle-tested, sin transitive deps

## Testing Strategy

- **Unit:** test_*.py en tests/unit/ (mocks, no DB)
- **Integration:** test_*.py en tests/integration/ (real DB, fixtures)
- **E2E:** Abarcado por journey_smoke (fase después)

## Rollout

1. **Phase 1:** Merge a develop (todos los cambios)
2. **Phase 2:** journey_smoke verifica end-to-end
3. **Phase 3:** Release gate (security, smell, etc.)
4. **Phase 4:** Merge a main + deploy a staging

## Backward Compatibility

- ✓ No breaking changes en APIs públicas
- ✓ Existing calls siguen funcionando (decorators son transparent)
- ✓ Nuevo schema audit_log no toca existing tables

## Performance Impact

| Operation | Before | After | Delta |
|-----------|--------|-------|-------|
| Gemini call (success) | ~500ms | ~510ms | +10ms (logging) |
| Google Calendar (success) | ~300ms | ~310ms | +10ms (logging) |
| Postgres query (success) | ~50ms | ~52ms | +2ms (logging) |
| Escalada (full flow) | ~1000ms | ~1050ms | +50ms (audit insert) |

**Acceptable:** <10% overhead en happy path, <1% en error path

## Observability

Nuevas métricas/logs:
- Circuit breaker state por servicio (Prometheus)
- Retry count distribution (Prometheus)
- Audit log queries por tool/user (SQL)
- Fallback usage rate (logs JSON)

## Config

Environment variables:
```bash
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
LOG_OUTPUT=stdout                 # stdout, file
CIRCUIT_BREAKER_THRESHOLD=5       # fallos antes de OPEN
CIRCUIT_BREAKER_TIMEOUT=30        # segundos OPEN
RETRY_MAX_ATTEMPTS=3
RETRY_BASE_DELAY=1
FALLBACK_ENABLED=true
```

## Notas

- Middleware es stateless (thread-safe)
- Circuit breaker state es in-memory (pierde al restart, OK para demo)
- Audit table debe ser backed up (compliance)
- Trace IDs no son confidenciales (seguros en logs)
