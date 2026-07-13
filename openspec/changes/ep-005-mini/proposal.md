# EP-005-MINI: Production Deployment Stack

## Why

Sistema solo existe en dev local (docker-compose, laptop). v1.0 requiere producción: 99% uptime, <500ms latency, deployment automatizado, alerting. Objetivo 4 del PRD ("Funcionar 24/7") necesita infraestructura confiable, no dev.

## What Changes

- Dockerfile multi-stage (build + runtime minimal)
- `docker-compose.prod.yml` con Gunicorn, Nginx, health checks
- GitHub Actions workflow: test → build → push → deploy
- Health check endpoints (`/health`, `/ready`)
- Prometheus metrics + alerting rules básicas
- Nginx config: rate limiting (10 req/min), reverse proxy, compression
- Runbooks: deploy, rollback, scale

Breaking changes: none. Nuevo stack es additive (coexiste con dev docker-compose.yml).

## Capabilities

### New Capabilities
- `containerization`: Dockerfile multi-stage, <500MB, Alpine runtime
- `ci-cd-pipeline`: GitHub Actions (test → build → push image → deploy)
- `health-checks`: `/health` + `/ready` endpoints, dependency probes (Postgres, Gemini, EspoCRM)
- `monitoring-alerting`: Prometheus metrics, Grafana dashboard template, alerts para uptime/latency
- `nginx-reverse-proxy`: Rate limiting per-IP (10 req/min), compression, security headers

### Modified Capabilities
- `webhook-security`: Proxy through Nginx con rate limiting (modifica endpoint access pattern)

## Impact

- **Code**: `main.py` adds `/health`, `/ready` endpoints; `agent/` exports Prometheus metrics (new decorator or middleware)
- **Infra**: Dockerfile, docker-compose.prod.yml, `.github/workflows/deploy.yml`, Nginx config, monitoring stack
- **APIs**: No breaking changes. `/health`, `/ready` son nuevos endpoints de ops (not exposed to users)
- **Dependencies**: Prometheus client library (Python), Nginx (base image), GitHub Actions runtime
- **Deployment**: Shifts from local docker-compose to cloud container orchestration (ECS, K8s, or managed Docker)

## Trazabilidad

**Épica:** EP-005-MINI  
**Historias:**
- HU-026: Dockerization (dockerfile, compose.prod)
- HU-027: CI/CD pipeline (GitHub Actions)
- HU-028: Health checks + monitoring (endpoints + Prometheus)
- HU-021: Lead notifications (scheduler + email)
- HU-003: 24/7 availability (infra readiness)

**Dependencias de éxito:**
- EP-001, EP-002, EP-003-MINI ya archivadas (cimientos + security)
- Credenciales en .env (deploy env vars)
- Cloud account o managed Docker service (staging/prod target)
