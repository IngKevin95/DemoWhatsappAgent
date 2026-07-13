# Spec: Retry Logic with Exponential Backoff

## Qué

Decorator `@retry()` + función `retry_operation()` que reintenta operaciones fallidas con backoff exponencial y jitter.

## Dónde

- `agent/middleware/retry.py` (nueva)
- Aplicado a: `integrations/google.py`, `integrations/espocrm.py`, `tools.py` (database calls)

## Por Qué

**Problema actual:**
- `brain.py` tiene retry manual para Gemini 429 (fix específico, no generalizable)
- `tools.py` sin retry en Google Calendar, EspoCRM, Firebird
- Latencias transitorias causan fallos inmediatos

**Solución:**
- Retry automático con espera progresiva
- Evita cascadas (jitter previene thundering herd)
- Aplicable uniformemente a todos los servicios

## Cómo Funciona

### Configuración

```python
@retry(max_attempts=3, base_delay=1, backoff_factor=2, jitter=True)
def mi_funcion():
    pass

# O función
resultado = retry_operation(mi_funcion, max_attempts=3, base_delay=1)
```

### Parámetros

| Param | Default | Rango | Nota |
|-------|---------|-------|------|
| `max_attempts` | 3 | 1-10 | intentos totales (incluye primero) |
| `base_delay` | 1 | 0.1-10 | segundos (para primer retry) |
| `backoff_factor` | 2 | 1-4 | multiplicador exponencial |
| `jitter` | True | bool | ±20% aleatorio |
| `retryable_exceptions` | (ConnectionError, TimeoutError) | tuple | qué errores reintentar |

### Cálculo de Delay

```
delay = base_delay * (backoff_factor ^ attempt) ± 20%
```

Ejemplo con base_delay=1, factor=2:
- Intento 1: fallo inmediato
- Intento 2: wait 1s
- Intento 3: wait 2s
- Intento 4: wait 4s (máx 16s)

### Sync vs Async

```python
# Sync
resultado = retry_operation(sync_func)

# Async
resultado = await retry_operation(async_func, is_async=True)
```

## Aplicaciones Inmediatas

### 1. Google APIs (google.py)

```python
@retry(max_attempts=3, base_delay=0.5)
def crear_evento_calendar(titulo, fecha, hora):
    # llamada a Google Calendar API
    pass
```

**Por qué:** Google retorna 503 (temporarily unavailable)

### 2. EspoCRM API (espocrm.py)

```python
@retry(max_attempts=3, base_delay=1)
def crear_case_espocrm(nombre, telefono, descripcion):
    # POST a EspoCRM
    pass
```

**Por qué:** EspoCRM puede timeout en latencia alta

### 3. Firebird Queries (tools.py)

```python
def consultar_licencia(cliente_id):
    def query():
        # Firebird query
        pass
    return retry_operation(query, max_attempts=2, base_delay=0.1)
```

**Por qué:** Firebird connection pooling puede temporalmente fallar

## Testing

Ver `tests/unit/test_retry_logic.py`:
- ✓ Sucede en primer intento
- ✓ Reintenta tras falla transitoria
- ✓ Agota intentos y lanza error
- ✓ Backoff exponencial real
- ✓ Jitter varía los timings
- ✓ Async/await compatible
- ✓ Decorator funciona
- ✓ Solo reintenta excepciones específicas

## Métricas

- Tests: ≥8 casos
- Coverage: >90% en retry.py
- Max latency impact: <1s (backoff máximo 16s es aceptable)
- Error reduction: ≥20% (métricas post-deployment)

## Notas

- No reintenta en ValueError, TypeError (errores de lógica)
- Reintenta en ConnectionError, TimeoutError, requests.Timeout
- Jitter es determinista (seeded si test requires reproducibilidad)
- Log cada intento a DEBUG level
