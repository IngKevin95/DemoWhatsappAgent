---
id: FIX-REPAIR-003
titulo: Retry Consistency EspoCRM (EP-002-1)
epica: EP-REPAIRS
prioridad: MUST
complejidad: 1
estado: lista
---

# FIX-REPAIR-003: Retry Consistency

## AC-1: EspoCRM usa @retry decorator
**Given** `integrations/espocrm.py` calls EspoCRM API  
**When** call fails  
**Then** uses same `@retry` decorator as Google (exponential backoff 2/4/8s, max 3)

## AC-2: Backoff Timing
**Given** EspoCRM timeout on attempt 1  
**When** retry logic runs  
**Then** timing is 2s, 4s, 8s (not immediate retry)

## AC-3: Consistency with Google
**Given** both Google and EspoCRM integrations  
**When** either fails  
**Then** both use identical retry strategy (same decorator, same backoff)

## AC-4: Load Test
**Given** EspoCRM rate limit triggered (5 failures)  
**When** load test runs  
**Then** backoff timings observed in logs, consistent with exponential curve

## Código Afectado
- `agent/integrations/espocrm.py` — replace hardcoded retry loop with @retry decorator
- Tests: `tests/integration/test_espocrm_retry_backoff.py`

## Effort
- Código: 3h
- Tests: 1h
- Total: 4h

---
