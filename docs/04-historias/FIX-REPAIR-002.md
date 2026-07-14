---
id: FIX-REPAIR-002
titulo: Circuit Breaker en LLM (EP-002-2), para cumplir requerimientos de negocio
epica: EP-REPAIRS
prioridad: MUST
complejidad: 2
estado: lista
---

# FIX-REPAIR-002: Circuit Breaker LLM

## AC-1: Decorator Aplicado
**Given** `brain.py::generar_respuesta()` calls LLM  
**When** circuit breaker trips (3+ failures in 30s)  
**Then** decorator catches, returns fallback: "Disculpa, estoy ocupado. ¿Puedes reformular?"

## AC-2: Fallback Dinámica
**Given** user in conversation context  
**When** fallback triggered  
**Then** response includes user name if available (personalized fallback)

## AC-3: Config from ENV
**Given** `.env` has `CIRCUIT_BREAKER_THRESHOLD=3` and `CIRCUIT_BREAKER_WINDOW_SEC=30`  
**When** app starts  
**Then** circuit breaker uses those values

## AC-4: Load Test
**Given** LLM API fails 10× consecutively  
**When** load test runs  
**Then** circuit breaker trips, fallback sent, conversación continues (no cascade)

## Código Afectado
- `agent/brain.py::generar_respuesta()` — wrap client.messages.create() with @circuit_breaker
- `agent/middleware/circuit_breaker.py` — enhance existing decorator
- Tests: `tests/unit/test_brain_circuit_breaker.py`, `tests/e2e/test_generar_respuesta_fallback.py`

## Effort
- Código: 4h
- Tests: 2h
- Total: 6h

---
