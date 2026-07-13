# Unit Tests: main.py

## Descripción

Tests de validación de webhook, rate limiting, input sanitization.

## Requisitos

### R1: Validación de firma HMAC Meta correcta
**Given** webhook payload + firma HMAC válida  
**When** se llama POST /webhook con payload + X-Hub-Signature-256  
**Then** verifica_firma_meta() retorna True, webhook se procesa

### R2: Firma HMAC incorrecta rechazada
**Given** webhook payload con firma HMAC falsa  
**When** se llama POST /webhook con firma inválida  
**Then** verifica_firma_meta() retorna False, webhook retorna 403 Forbidden

### R3: Rate limiting 10 req/min por IP
**Given** mismo IP envía 15 requests en 60s  
**When** request 11-15 llegan  
**Then** retorna 429 Too Many Requests, headers incluyen Retry-After

### R4: Input sanitization en mensaje
**Given** usuario envía mensaje con "<script>alert('xss')</script>"  
**When** se procesa en recibir_webhook (sanitize_input)  
**Then** script tags removidos, mensaje limpio pasado a brain.py

## Artefactos

- `tests/unit/test_main.py` (ampliación de existente)
- Mock Meta webhook generator en conftest.py

## Criterios de Aceptación

- ≥8 test cases en test_main.py
- Todos pasan: `pytest tests/unit/test_main.py -v`
- Coverage de recibir_webhook, verifica_firma_meta, rate_limit ≥90%
- Rate limiting se dispara correctamente en umbral 11
