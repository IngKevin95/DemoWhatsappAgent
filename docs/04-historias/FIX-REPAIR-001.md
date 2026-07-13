---
id: FIX-REPAIR-001
titulo: Sanitizar tokens en exception logs (EP-002-3)
epica: EP-REPAIRS
prioridad: MUST
complejidad: 1
estado: lista
---

# FIX-REPAIR-001: Tokens en Logs (Security)

## AC-1: Exception Logging Sanitizado
**Given** exception occurs en `integrations/google.py:45`  
**When** logger captures `response.text`  
**Then** Authorization/access_token fields redacted (replaced with `[REDACTED]`)

## AC-2: Token Scrubbing in Handlers
**Given** exception handler catches API failure  
**When** exception logged  
**Then** all credential-like strings (token, password, api_key, DATABASE_URL) removed

## AC-3: CI Security Gate
**Given** CI runs tests  
**When** logs generated  
**Then** gate fails if regex finds token-like patterns (Authorization, access_token, Bearer)

## AC-4: Verification
**Given** new test suite runs  
**When** `tests/security/test_secrets_in_exceptions.py` executes  
**Then** grep finds 0 credential matches in exception logs

## Código Afectado
- `agent/middleware/logging.py` — add sanitizer
- `agent/integrations/google.py:45` — wrap with sanitizer
- Tests: `tests/security/test_secrets_in_exceptions.py` (nuevo)

## Effort
- Código: 2h
- Tests: 1h
- Total: 3h

---
