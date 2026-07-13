# Spec: Structured Logging (JSON)

## Qué

Logger configurado para salida JSON estructurada con scrubbing de secrets.

## Dónde

- `agent/middleware/logging.py` (nueva)
- Aplicado en: `main.py`, `brain.py`, `tools.py`, `integrations/*.py`

## Por Qué

**Problema actual:**
- Logs de texto sin estructura (grep manual necesario)
- Secrets visibles en logs (DATABASE_URL, GOOGLE_*, META_*)
- Sin trace_id (correlación entre eventos imposible)
- Sin levels sistemáticos (DEBUG vs INFO)

**Solución:**
- JSON output: machine parseable
- Secrets scrubber: mascarar tokens antes de escribir
- trace_id: correlacionar eventos del mismo webhook
- Levels claros: DEBUG (Postgres queries), INFO (tool calls), WARNING (retry), ERROR (circuit), CRITICAL (service down)

## Formato

```json
{
  "timestamp": "2026-07-13T23:30:45.123Z",
  "level": "INFO",
  "service": "bot",
  "module": "brain",
  "message": "Generated response",
  "trace_id": "webhook-12345-abc",
  "user_phone": "+573001234567",
  "tool": "consultar_precio_modulo",
  "duration_ms": 245,
  "metadata": {
    "modulo": "Soporte Avanzado",
    "precio": 150000
  }
}
```

## Levels

| Level | Cuándo | Ejemplo |
|-------|--------|---------|
| DEBUG | Detalle técnico bajo | PostgreSQL query, bytes enviados |
| INFO | Eventos normales | Tool call iniciado, resultado |
| WARNING | Comportamiento inesperado pero recuperable | Retry triggered, circuit abierto |
| ERROR | Error recoverable | API 500, timeout, falla en retry final |
| CRITICAL | Error no-recoverable | Servicio completamente down, crash inminente |

## Configuración

```python
from agent.middleware.logging import setup_structured_logging

# En main.py
setup_structured_logging(
    level="INFO",  # env var: LOG_LEVEL
    output="stdout",  # env var: LOG_OUTPUT (stdout, file)
    secrets_to_scrub=[
        "DATABASE_URL",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_OAUTH_TOKEN",
        "META_API_TOKEN",
        "FIREBIRD_PASSWORD",
    ]
)

logger = logging.getLogger(__name__)
```

## Uso

```python
# En tools.py
logger.info(
    "Tool execution",
    extra={
        "tool": "escalar_a_humano",
        "user_phone": user_phone,
        "case_id": case_id,
        "duration_ms": elapsed_ms,
        "trace_id": trace_id,
    }
)

# Con error
logger.error(
    "Tool failed",
    extra={
        "tool": "agendar_cita",
        "error": str(e),
        "trace_id": trace_id,
    },
    exc_info=True  # stack trace incluido
)
```

## Secrets Scrubber

Reemplaza valores sensibles:
```python
"DATABASE_URL": "postgre://***@***:***",
"GOOGLE_APPLICATION_CREDENTIALS": "[REDACTED]",
"FIREBIRD_PASSWORD": "***",
```

Implementación:
```python
def scrub_secrets(log_record, secrets_pattern):
    for key in secrets_pattern:
        if key in log_record.msg:
            log_record.msg = log_record.msg.replace(
                key_value, f"{key[:3]}***"
            )
    return log_record
```

## trace_id Propagation

trace_id nace en webhook (main.py):
```python
trace_id = f"webhook-{datetime.now().timestamp()}-{uuid4()[:8]}"
# Pasa a brain -> tools -> integrations
```

Disponible en contexto:
```python
import contextvars
trace_id = get_trace_id()  # contextvars.ContextVar
logger.info("message", extra={"trace_id": trace_id})
```

## Integración con Middleware

Retry + Circuit Breaker loguean automáticamente:

```python
# retry.py
logger.warning(
    "Retry triggered",
    extra={
        "attempt": attempt,
        "delay_s": delay,
        "trace_id": trace_id,
    }
)

# circuit_breaker.py
logger.warning(
    "Circuit breaker opened",
    extra={
        "service": "google_calendar",
        "failure_threshold": 5,
        "recovery_timeout": 30,
    }
)
```

## Ejemplo: Auditoría de Escalamiento

```python
# En escalar_a_humano
logger.info(
    "Case escalated",
    extra={
        "user_phone": user_phone,
        "case_id": case_id,
        "reason": "license_expired",
        "trace_id": trace_id,
        "timestamp": datetime.now().isoformat(),
    }
)
```

Resultado:
```json
{
  "timestamp": "2026-07-13T23:35:10.456Z",
  "level": "INFO",
  "service": "bot",
  "module": "tools",
  "message": "Case escalated",
  "trace_id": "webhook-12345-xyz",
  "user_phone": "+573001234567",
  "case_id": 98765,
  "reason": "license_expired"
}
```

## Testing

Ver `tests/unit/test_logging.py`:
- ✓ JSON output válido
- ✓ Secrets scrubbed en output
- ✓ trace_id propagado
- ✓ Levels respetados
- ✓ Stack trace incluido en ERROR/CRITICAL

## Métricas de Éxito

- Tests: ≥6 casos
- Coverage: >90% en logging.py
- No secrets visible: 0 falsos positivos en scan
- Log latency: <1ms por evento

## Notas

- No loguear full chat history (volumen). Solo resumen.
- No loguear user_phone completo si posible (privacy). Formato: +57300****567
- trace_id útil para correlación ELK/Datadog/Sentry
