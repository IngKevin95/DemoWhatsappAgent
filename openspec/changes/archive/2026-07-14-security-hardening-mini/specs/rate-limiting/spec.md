# Specification: Rate Limiting

Proteger el webhook contra ataques DDoS básicos limitando requests a 10 por minuto por IP origen.

## ADDED Requirements

### Requirement: Rate Limit Enforcement per IP
El sistema SHALL limitar requests a 10 por minuto por dirección IP origen. Requests posteriores al límite retornan HTTP 429 Too Many Requests y NO se procesan.

#### Scenario: Limit enforced at 11th request
- **WHEN** dirección IP envía 11 requests en 60 segundos
- **THEN** el 11° request recibe HTTP 429 con mensaje "Too many requests. Límite: 10 req/min por IP"
- **AND** el request NO llega a Gemini ni a herramientas
- **AND** sistema loguea evento: source_ip, attempts_count, timestamp, action="rate_limited"

#### Scenario: Limit does not affect different IPs
- **WHEN** IP-A alcanza el límite de 10 requests
- **THEN** IP-B puede enviar requests normalmente (sin bloqueo)
- **AND** cada IP mantiene contador independiente

#### Scenario: Limit resets after 1 minute
- **WHEN** IP fue limitada hace 61 segundos
- **THEN** nuevo request es aceptado (contador reset a 0)
- **AND** HTTP 200 respuesta normal
- **AND** sistema loguea: reset_event, source_ip, timestamp

### Requirement: X-Forwarded-For Header Support
El sistema SHALL extraer la dirección IP real del cliente desde el header X-Forwarded-For cuando está presente (CDN/proxy scenario).

#### Scenario: X-Forwarded-For with proxy chain
- **WHEN** request incluye header X-Forwarded-For: "203.0.113.10, 198.51.100.5, 192.0.2.1" (client, proxy1, proxy2)
- **THEN** rate limiter usa primer valor (203.0.113.10) como client_ip
- **AND** contador es por 203.0.113.10, no por IPs de proxy
- **AND** sistema loguea: client_ip (extracted), proxy_chain, trusted_proxy_verified

#### Scenario: X-Forwarded-For absent, use socket IP
- **WHEN** request SIN header X-Forwarded-For
- **THEN** rate limiter usa dirección IP directa del socket TCP
- **AND** rate limit se aplica normal

### Requirement: Rate Limiting Configuration
Límites y ventana de tiempo SHALL ser configurables vía variables de entorno.

#### Scenario: Config applied from .env
- **WHEN** archivo .env contiene RATE_LIMIT_REQUESTS=10, RATE_LIMIT_WINDOW_SECONDS=60
- **THEN** middleware usa estos valores (no hardcoded)
- **AND** cambios en .env toman efecto en próximo restart

### Requirement: Rate Limit Logging
Todos los eventos de rate limiting SHALL loguear en formato JSON con campos: source_ip, requests_count, action, timestamp.

#### Scenario: Rate limit log entry
- **WHEN** IP es rate limitada
- **THEN** log contiene: {"source_ip": "...", "requests_count": 11, "action": "rate_limited", "timestamp": "2026-07-14T15:30:45Z"}
- **AND** timestamp es ISO 8601 UTC
