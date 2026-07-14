# Nginx Reverse Proxy Specification

## ADDED Requirements

### Requirement: Reverse Proxy Configuration
The system SHALL route incoming HTTP traffic through Nginx to Gunicorn backend.

#### Scenario: Nginx listens on port 80
- **WHEN** Nginx container starts
- **THEN** listens on 0.0.0.0:80 and forwards requests to Gunicorn backend (http://app:8000)

#### Scenario: Backend health check
- **WHEN** requests arrive at Nginx
- **THEN** Nginx uses proxy_pass to forward to Gunicorn, with fallback 502 if backend unavailable

#### Scenario: Connection upgrade for WebSockets
- **WHEN** WebSocket upgrade request is received (Upgrade: websocket header)
- **THEN** Nginx forwards upgrade headers and establishes WebSocket connection to backend

### Requirement: Rate Limiting
The system SHALL enforce 10 requests per minute per IP on the webhook endpoint.

#### Scenario: Rate limit zone definition
- **WHEN** Nginx configuration is loaded
- **THEN** defines limit_req_zone with key $binary_remote_addr, zone=webhook_limit, rate=10r/m

#### Scenario: Webhook endpoint rate limited
- **WHEN** location /agentes/liberar is configured
- **THEN** applies limit_req zone=webhook_limit burst=2 nodelay

#### Scenario: Rate limit enforcement
- **WHEN** a client exceeds 10 requests per minute from single IP
- **THEN** 11th request returns 429 Too Many Requests

#### Scenario: Burst handling
- **WHEN** burst=2 is configured
- **THEN** up to 2 additional requests are queued; 13th request and beyond rejected

#### Scenario: Other endpoints not rate limited
- **WHEN** requests to /health, /metrics, /ready, or other bot endpoints occur
- **THEN** no rate limiting applied (only /agentes/liberar endpoint is limited)

### Requirement: Response Compression
The system SHALL compress response bodies to reduce bandwidth.

#### Scenario: Gzip compression enabled
- **WHEN** Nginx configuration is loaded
- **THEN** gzip on, with compression types: text/html, application/json, text/plain, text/css, application/javascript

#### Scenario: Compression applied
- **WHEN** client sends Accept-Encoding: gzip header
- **THEN** Nginx compresses response if > 1KB; level 6 (moderate compression)

### Requirement: Security Headers
The system SHALL add security headers to responses.

#### Scenario: HSTS header
- **WHEN** response is sent
- **THEN** includes Strict-Transport-Security: max-age=31536000; includeSubDomains header

#### Scenario: X-Frame-Options header
- **WHEN** response is sent
- **THEN** includes X-Frame-Options: DENY (prevent clickjacking)

#### Scenario: X-Content-Type-Options header
- **WHEN** response is sent
- **THEN** includes X-Content-Type-Options: nosniff (prevent MIME sniffing)

#### Scenario: CSP header
- **WHEN** response is sent
- **THEN** includes Content-Security-Policy: default-src 'self' (basic CSP, can be customized)

### Requirement: Nginx Configuration File
The system SHALL provide nginx.conf or nginx/default.conf in docker-compose.prod.yml volume mount.

#### Scenario: Config file included
- **WHEN** Nginx container starts
- **THEN** mounts nginx.conf from docker volume or config file

#### Scenario: Config is version controlled
- **WHEN** repository is cloned
- **THEN** nginx configuration file(s) are included in git

### Requirement: Logging
The system SHALL log HTTP requests for debugging.

#### Scenario: Access logs
- **WHEN** requests are processed
- **THEN** Nginx logs access to /var/log/nginx/access.log with format: $remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"

#### Scenario: Error logs
- **WHEN** errors occur (backend timeout, connection refused, etc.)
- **THEN** Nginx logs to /var/log/nginx/error.log with level warn or higher

#### Scenario: Logs are accessible
- **WHEN** debugging is needed
- **THEN** logs are available in container stdout (via Docker logging driver) or persistent volume

### Requirement: Nginx in Docker Compose
The system SHALL orchestrate Nginx as a service in docker-compose.prod.yml.

#### Scenario: Nginx service definition
- **WHEN** docker-compose prod stack starts
- **THEN** Nginx service (nginx:latest) is defined with proper port mapping (80:80), volume mounts (config, logs), and health check

#### Scenario: Network isolation
- **WHEN** Nginx and Gunicorn containers start
- **THEN** both connect to same Docker network (app_network), allowing Nginx to reach Gunicorn via service name (http://app:8000)
