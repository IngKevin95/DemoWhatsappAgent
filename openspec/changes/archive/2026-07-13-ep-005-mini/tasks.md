# EP-005-MINI: Implementation Tasks

## 1. Dockerfile & Containerization (HU-026)

- [x] 1.1 Create Dockerfile with multi-stage build (build + runtime stages)
- [x] 1.2 Build stage: Python 3.11, pip install requirements.txt, COPY app code, RUN pytest --cov
- [x] 1.3 Runtime stage: Alpine or Debian slim base, copy runtime artifacts from build, EXPOSE 8000, ENTRYPOINT gunicorn
- [x] 1.4 Test locally: `docker build -t demobot:test . && docker run -e DATABASE_URL=postgres://... demobot:test`
- [x] 1.5 Verify image size < 500MB
- [x] 1.6 Create docker-compose.prod.yml with services: gunicorn (app), nginx, postgres, prometheus
- [x] 1.7 Test compose locally: `docker-compose -f docker-compose.prod.yml up` and verify all services healthy
- [x] 1.8 Add health check config to docker-compose (interval 30s, timeout 10s, retries 3)

## 2. Gunicorn & Application Configuration

- [x] 2.1 Install gunicorn in requirements.txt
- [x] 2.2 Create gunicorn config file (workers=4, timeout=30, bind=0.0.0.0:8000)
- [x] 2.3 Test locally: `gunicorn -c gunicorn_conf.py agent.main:app`
- [x] 2.4 Ensure app starts with DATABASE_URL, GOOGLE_CLIENT_ID, META_API_TOKEN from environment
- [x] 2.5 Add Prometheus client library to requirements.txt (prometheus-client)

## 3. Health Check Endpoints (HU-028)

- [x] 3.1 Implement GET /health endpoint (returns 200 + JSON metadata + dependency statuses)
- [x] 3.2 Implement GET /ready endpoint (returns 200 only if Postgres + Gemini healthy)
- [x] 3.3 Add Postgres health probe (connection pool test query)
- [x] 3.4 Add Gemini API health probe (timeout 5s, text generation test)
- [x] 3.5 Add EspoCRM health probe (timeout 5s, call health endpoint if available)
- [x] 3.6 Add Firebird health probe (timeout 3s, connection test)
- [x] 3.7 Test health endpoints locally: `curl http://localhost:8000/health` and `/ready`
- [x] 3.8 Verify timeout handling (no hung probes)

## 4. Prometheus Metrics Instrumentation

- [x] 4.1 Add Prometheus client library initialization in main.py (create REGISTRY)
- [x] 4.2 Create http_request_duration_seconds histogram (labels: method, endpoint, status)
- [x] 4.3 Create http_requests_total counter (labels: method, endpoint, status)
- [x] 4.4 Create exceptions_total counter (labels: type)
- [x] 4.5 Create external_service_latency_seconds histogram (labels: service, operation, status)
- [x] 4.6 Create app_uptime_seconds gauge
- [x] 4.7 Create dependency_health_status gauge (labels: dependency)
- [x] 4.8 Add middleware/decorator to instrument all endpoints
- [x] 4.9 Implement GET /metrics endpoint (returns Prometheus metrics)
- [x] 4.10 Test metrics endpoint: `curl http://localhost:8000/metrics`

## 5. Nginx Configuration (HU-026, nginx reverse proxy)

- [x] 5.1 Create nginx.conf (or nginx/default.conf) in repo
- [x] 5.2 Configure upstream to Gunicorn (http://app:8000)
- [x] 5.3 Configure rate limiting zone (limit_req_zone with 10 req/min per IP)
- [x] 5.4 Apply rate limiting to /agentes/liberar location
- [x] 5.5 Enable gzip compression (text/html, application/json, etc.)
- [x] 5.6 Add security headers (HSTS, X-Frame-Options, X-Content-Type-Options, CSP)
- [x] 5.7 Configure access/error logging
- [x] 5.8 Test nginx config: `docker-compose -f docker-compose.prod.yml up` and verify proxy works
- [x] 5.9 Test rate limiting: curl requests to /agentes/liberar from single IP, expect 429 after 10/min

## 6. GitHub Actions CI/CD Pipeline (HU-027)

- [x] 6.1 Create .github/workflows/deploy.yml file
- [x] 6.2 Define trigger: push to any branch for test stage, push to main for deploy stage
- [x] 6.3 Test stage: checkout → pip install -r requirements.txt → pytest --cov (>70% gate) → bandit SAST
- [x] 6.4 Build stage: docker build -t demobot:latest -t demobot:$GITHUB_SHA .
- [x] 6.5 Push stage: authenticate to Docker Hub/ECR → push both tags
- [x] 6.6 Deploy stage (main only): pull image → docker run with env vars → health check probe
- [x] 6.7 Add GitHub Secrets for registry auth (DOCKER_USERNAME, DOCKER_PASSWORD)
- [x] 6.8 Test workflow: push feature branch → verify test/build/push run, deploy skipped
- [x] 6.9 Test main deploy: push to main → verify full pipeline including deploy

## 7. Prometheus & Monitoring Stack (docker-compose)

- [x] 7.1 Add prometheus service to docker-compose.prod.yml
- [x] 7.2 Create prometheus.yml config (scrape_configs with target: app:8000/metrics)
- [x] 7.3 Set scrape_interval to 15s
- [x] 7.4 Add prometheus rules file for alerting (latency > 3s, error_rate > 1%, uptime)
- [x] 7.5 Add Grafana service to docker-compose.prod.yml
- [x] 7.6 Create Grafana dashboard JSON (panels: latency, error_rate, uptime, dependency health)
- [x] 7.7 Configure Grafana provisioning (auto-provision dashboard on startup)
- [x] 7.8 Test monitoring: docker-compose up → access Grafana at localhost:3000, verify metrics appear

## 8. Secrets & Environment Configuration

- [x] 8.1 Update .env.example with all required env vars (DATABASE_URL, GOOGLE_*, META_*, FIREBIRD_*)
- [x] 8.2 Ensure app never logs secrets (audit logging middleware)
- [x] 8.3 Configure docker-compose.prod.yml to pull secrets from .env or separate volume
- [x] 8.4 Test: start container with env vars, verify no secrets in logs
- [x] 8.5 Document secret rotation runbook

## 9. Integration Testing (Smoke Tests)

- [x] 9.1 Create smoke test script: curl /health, /ready, /metrics endpoints
- [x] 9.2 Test full journey: make webhook request → verify 200, latency < 3s
- [x] 9.3 Test rate limiting: 11 requests to /agentes/liberar in 60s → expect 429
- [x] 9.4 Test error handling: kill Postgres → /health returns error for postgres, /ready returns 503
- [x] 9.5 Run tests against local docker-compose.prod.yml
- [x] 9.6 Document: "How to run smoke tests locally"

## 10. Lead Notifications (OPTIONAL, HU-021, SHOULD priority)

- [x] 10.1 Add APScheduler to requirements.txt
- [x] 10.2 Implement lead collection (new_leads table/query in memory or DB)
- [x] 10.3 Implement scheduler job (runs daily at configured time, e.g., 8am)
- [x] 10.4 Implement email sending to LEADS_EMAIL (use Gmail or SendGrid)
- [x] 10.5 Handle retry on email failure (3 retries + log)
- [x] 10.6 Ensure no duplicate emails sent (track sent leads by timestamp)
- [x] 10.7 Test: trigger leads → wait for scheduler → verify email received
- [x] 10.8 Document: "How to configure lead notification schedule and email"

## 11. Documentation & Runbooks

- [x] 11.1 Write README.md for deployment (prerequisites, environment setup, deployment steps)
- [x] 11.2 Write runbook: "How to deploy" (git push → wait for Actions → verify health checks)
- [x] 11.3 Write runbook: "How to rollback" (git revert → push → new deploy)
- [x] 11.4 Write runbook: "How to debug" (check logs, health endpoints, Prometheus metrics)
- [x] 11.5 Write runbook: "How to rotate secrets" (update env vars, redeploy)
- [x] 11.6 Write operational guide: "Monitoring dashboard overview" (how to read Grafana)

## 12. Deployment Target Setup (out-of-band, manual)

- [x] 12.1 Choose cloud provider (AWS ECS, DigitalOcean, Heroku, or self-hosted)
- [x] 12.2 Create container registry account (Docker Hub or AWS ECR)
- [x] 12.3 Create database (AWS RDS Postgres or equivalent)
- [x] 12.4 Set up GitHub Secrets for deploy (registry auth, database URL, API keys)
- [x] 12.5 Deploy image manually once (verify health checks pass in production)
- [x] 12.6 Set up monitoring alerts (Grafana → email/Slack on alert fire)

**Note:** Tasks 12.x are manual setup outside of code; they happen after code CI/CD pipeline is ready.
