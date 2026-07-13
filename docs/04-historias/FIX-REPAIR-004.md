---
id: FIX-REPAIR-004
titulo: Timeout en Gemini (EP-001-3)
epica: EP-REPAIRS
prioridad: MUST
complejidad: 1
estado: lista
---

# FIX-REPAIR-004: Timeout Gemini + Config

## AC-1: Timeout Explícito
**Given** `brain.py::generar_respuesta()` calls `client.messages.create()`  
**When** call made  
**Then** timeout=10s parameter applied (max 10 seconds)

## AC-2: Timeout Config from ENV
**Given** `.env` has `GEMINI_TIMEOUT_SECONDS=10`  
**When** app starts  
**Then** timeout value loaded and applied to Gemini calls

## AC-3: Yellow Zone Logging
**Given** Gemini call takes >5s  
**When** response received  
**Then** warning logged: "Gemini latency high: 5.3s (approaching timeout)"

## AC-4: Integration with Circuit Breaker
**Given** Gemini timeout occurs (10s exceeded)  
**When** timeout caught  
**Then** circuit breaker catches exception, triggers fallback

## Código Afectado
- `agent/brain.py::generar_respuesta()` — add timeout=10 to client.messages.create()
- `.env.example` — add GEMINI_TIMEOUT_SECONDS=10
- Tests: `tests/unit/test_brain_timeout.py`

## Effort
- Código: 2h
- Tests: 2h
- Total: 4h

---
