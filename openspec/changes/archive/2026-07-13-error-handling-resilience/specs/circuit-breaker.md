# Spec: Circuit Breaker Pattern

## Qué

Circuit breaker wrapper alrededor de Pybreaker para fallar rápido cuando servicios están degradados.

## Dónde

- `agent/middleware/circuit_breaker.py` (nueva)
- Integrado en: `integrations/google.py`, `integrations/espocrm.py`, `integrations/firebird.py`

## Por Qué

**Problema actual:**
- Latencias en cascada: si Google Calendar timeout, otros usuarios esperan su retry
- Sin fail-fast: cada error consume max_attempts * delay (wasteful)
- Sin recovery: si servicio vuelve, no lo detectamos

**Solución:**
- Circuit breaker: CLOSED (normal) → OPEN (fail-fast) → HALF_OPEN (test recovery) → CLOSED
- Evita cascadas exponenciales
- Detecta automáticamente cuando servicio se recupera

## Estados

### CLOSED (Normal)
- Todas las llamadas pasan
- Tally de fallos en reset
- Transición: 5 fallos en 60s → OPEN

### OPEN (Fail-Fast)
- Todas las llamadas lanzan CircuitBreakerOpen inmediatamente
- Sin llamadas reales al servicio
- Timeout 30s → HALF_OPEN

### HALF_OPEN (Testing Recovery)
- 1 llamada pasa al servicio (test)
- Si sucede: CLOSED
- Si falla: OPEN (reset timeout a 30s más)

## Configuración

```python
from agent.middleware.circuit_breaker import CircuitBreaker

breaker_google = CircuitBreaker(
    name="google_calendar",
    failure_threshold=5,      # fallos antes de OPEN
    recovery_timeout=30,      # segundos en OPEN antes de HALF_OPEN
    expected_exception=Exception,
)

@breaker_google
def crear_evento():
    # Google Calendar API call
    pass
```

## Aplicaciones

### 1. Google APIs

```python
breaker_google = CircuitBreaker("google", failure_threshold=5, recovery_timeout=30)

@breaker_google
def crear_evento_calendar(...):
    return google.calendar.events().create(...)
```

**Threshold:** 5 fallos → OPEN (Google SLA: <500ms, >5 timeout = problema)

### 2. EspoCRM

```python
breaker_crm = CircuitBreaker("espocrm", failure_threshold=5, recovery_timeout=30)

@breaker_crm
def crear_case_crm(...):
    return espocrm.api.post("/cases", ...)
```

### 3. Gemini API

```python
breaker_gemini = CircuitBreaker("gemini", failure_threshold=3, recovery_timeout=60)

@breaker_gemini
def generar_respuesta(mensaje):
    return genai.Client().models.generate_content(...)
```

**Threshold más bajo (3):** Gemini bajo carga rápido satura

## Errors

```python
class CircuitBreakerOpen(Exception):
    """Circuit abierto, servicio rechazando."""
    pass
```

Caller debe manejar:
```python
try:
    resultado = crear_evento_calendar()
except CircuitBreakerOpen:
    # Fallback response (ver fallback-responses.md)
    return "Sistema de calendario no disponible. Te contactamos pronto."
```

## Monitoreo

Logs (structured):
```json
{"level": "WARNING", "service": "google_calendar", "event": "circuit_open", "recovery_in": 30}
{"level": "INFO", "service": "google_calendar", "event": "half_open_attempt"}
{"level": "INFO", "service": "google_calendar", "event": "circuit_closed"}
```

Métricas (Prometheus):
- `circuit_breaker_state{service="google"}` → 0 (CLOSED), 1 (OPEN), 2 (HALF_OPEN)
- `circuit_breaker_failures_total{service="google"}`
- `circuit_breaker_recoveries_total{service="google"}`

## Testing

Ver `tests/unit/test_circuit_breaker.py`:
- ✓ Estado CLOSED: llamadas pasan
- ✓ Transición CLOSED → OPEN: después de threshold fallos
- ✓ Estado OPEN: lanzan CircuitBreakerOpen inmediato
- ✓ Timeout OPEN → HALF_OPEN
- ✓ HALF_OPEN + success → CLOSED
- ✓ HALF_OPEN + failure → OPEN (reset timeout)
- ✓ Métricas se registran

## Métricas de Éxito

- Tests: ≥8 casos
- Coverage: >85% en circuit_breaker.py
- Latency improvement: <100ms (vs retry exhaustion)
- Recovery detection: <60s (OPEN timeout)

## Integración con Retry

```
retry_operation(
    @breaker_wrapped_function,
    max_attempts=3
)
```

**Flujo:**
1. Intento 1: CLOSED, falla, retry después de 1s
2. Intento 2: CLOSED, falla, retry después de 2s
3. Intento 3: OPEN, lanzan CircuitBreakerOpen → catch + fallback

**Efecto:** Sin circuit breaker, esperaría 3s. Con breaker, fail-fast en intento 3.
