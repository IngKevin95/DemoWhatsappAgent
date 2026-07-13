# Spec: Fallback Responses on Service Degradation

## Qué

Respuestas pre-grabadas cuando servicios externos están down o sin respuesta.

## Dónde

- `agent/middleware/fallback.py` (nueva)
- Aplicado en: `brain.py`, `tools.py` (en bloques try-except de integración)

## Por Qué

**Problema actual:**
- Si Gemini timeout: bot queda mudo (experiencia nula)
- Si Google Calendar down: no puedo agendar (pero sí podría escapar gracefully)
- Si EspoCRM error: escalada falla sin mensaje al usuario

**Solución:**
- Fallback responses graceful:
  - Gemini timeout → "Estoy un poco lento, intenta en unos segundos"
  - Google Calendar down → "Tu cita se agendar pronto"
  - EspoCRM error → "Un agente te llamará"
  - Firebird down → "Verificaré tu licencia más tarde"

## Respuestas por Servicio

### Gemini (generar_respuesta)

```python
try:
    respuesta = genai.Client().models.generate_content(...)
except (TimeoutError, DeadlineExceeded):
    # Después de 3 retries agotados
    respuesta = FALLBACK_GEMINI_TIMEOUT
    logger.warning("Gemini timeout, fallback response", extra={...})
```

**Fallback:**
```
"Disculpa, estoy un poco lento en este momento. ¿Puedes repetir tu pregunta?"
```

### Google Calendar (agendar_cita)

```python
try:
    event = google.calendar.events().create(...)
except HttpError as e:
    if e.resp.status in [500, 503]:  # Service Unavailable
        return {
            "status": "pending",
            "message": "Tu cita está en cola. Te enviaré los detalles pronto."
        }
```

**Fallback:**
```
"Tu cita se agendar pronto. Te enviaré los detalles a WhatsApp."
```

### EspoCRM (escalar_a_humano, crear_lead)

```python
try:
    case = espocrm.api.post("/cases", data)
except (ConnectionError, requests.Timeout):
    return {
        "status": "escalated_async",
        "message": "Tu caso fue registrado. Un agente te llamará en menos de 2 horas."
    }
```

**Fallback:**
```
"Un agente de soporte te contactará pronto. Por favor espera nuestra llamada."
```

### Firebird (consultar_licencia, reclasificar_caso)

```python
try:
    resultado = firebird.query(...)
except (fb.DatabaseError, ConnectionError):
    return {
        "status": "unknown",
        "message": "No puedo verificar tu licencia ahora. Confirmaré después."
    }
```

**Fallback:**
```
"Tu estado de licencia no está disponible momentáneamente. Te confirmaré después."
```

## Implementación

```python
# agent/middleware/fallback.py

FALLBACK_RESPONSES = {
    "gemini_timeout": "Disculpa, estoy un poco lento. Intenta de nuevo en unos segundos.",
    "gemini_error": "Hubo un problema procesando tu pregunta. Intenta más tarde.",
    
    "google_calendar_timeout": "Tu cita se agendar pronto. Te enviaré los detalles a WhatsApp.",
    "google_calendar_error": "No pude agendar ahora. Un agente te llamará pronto.",
    
    "espocrm_escalation_fail": "Tu caso fue registrado. Un agente te contactará pronto.",
    "espocrm_lead_fail": "Gracias por tu interés. Nos pondremos en contacto pronto.",
    
    "firebird_license_fail": "Tu estado de licencia se verificará más tarde.",
    "firebird_error": "Sistema de licencias no disponible. Validaremos después.",
}

def get_fallback(service, error_type):
    key = f"{service}_{error_type}"
    return FALLBACK_RESPONSES.get(key, "Intenta más tarde, por favor.")
```

## Decisión de Cuándo Usar

```
Intento 1: falla → retry
Intento 2: falla → retry
Intento 3: falla → CircuitBreakerOpen → fallback
```

**OR:**

```
Timeout > 3 segundos → fallback (sin reintentar)
```

### Ejemplos

**Gemini:**
```python
try:
    with timeout(3):  # 3s máximo
        respuesta = genai.generate(...)
except TimeoutError:
    return get_fallback("gemini", "timeout")
```

**Google Calendar (con retry + circuit breaker):**
```python
try:
    return await retry_operation(
        breaker_google(crear_evento_real),
        max_attempts=3
    )
except CircuitBreakerOpen:
    logger.warning("Google Calendar circuit open, using fallback")
    return get_fallback("google_calendar", "timeout")
```

## Analytics

Loguear cada fallback:
```python
logger.warning(
    "Fallback response used",
    extra={
        "service": "gemini",
        "error_type": "timeout",
        "user_phone": user_phone,
        "trace_id": trace_id,
    }
)
```

Query para analytics:
```sql
SELECT 
  metadata->>'service' as service,
  COUNT(*) as fallback_count
FROM audit_log
WHERE message LIKE '%Fallback response%'
  AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY service
ORDER BY fallback_count DESC;
```

## Testing

Ver `tests/unit/test_fallback_responses.py`:
- ✓ Fallback retornado en timeout
- ✓ Fallback retornado en CircuitBreakerOpen
- ✓ Fallback es humano-legible
- ✓ Fallback logged correctamente
- ✓ No re-envía si circuito ya abierto

## Métricas de Éxito

- Tests: ≥5 casos
- Coverage: >80% en fallback.py
- Fallback rate: <1% en producción (indicador de degradación)
- User perception: feedback positivo en fallback clarity

## Notas

- Fallback messages deben ser honestos (no promesas falsas)
- "Intenta más tarde" es mejor que silencio
- Cada fallback loguea automáticamente para tracking
- Fallbacks son localizables (futura: esp/eng)
