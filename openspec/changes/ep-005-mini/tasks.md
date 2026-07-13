# EP-005-MINI: Implementation Tasks

## 1. Dockerfile & Containerization (HU-026)

- [ ] 1.1 Create Dockerfile with multi-stage build (build + runtime stages)
- [ ] 1.2 Build stage: Python 3.11, pip install requirements.txt, COPY app code, RUN pytest --cov
- [ ] 1.3 Runtime stage: Alpine or Debian slim base, copy runtime artifacts from build, EXPOSE 8000, ENTRYPOINT gunicorn
- [ ] 1.4 Test locally: `docker build -t demobot:test . && docker run -e DATABASE_URL=postgres://... demobot:test`
- [ ] 1.5 Verify image size < 500MB
- [ ] 1.6 Create docker-compose.prod.yml with services: gunicorn (app), nginx, postgres, prometheus
- [ ] 1.7 Test compose locally: `docker-compose -f docker-compose.prod.yml up` and verify all services healthy
- [ ] 1.8 Add health check config to docker-compose (interval 30s, timeout 10s, retries 3)

## 2. Gunicorn & Application Configuration

- [ ] 2.1 Install gunicorn in requirements.txt
- [ ] 2.2 Create gunicorn config file (workers=4, timeout=30, bind=0.0.0.0:8000)
- [ ] 2.3 Test locally: `gunicorn -c gunicorn_conf.py agent.main:app`
- [ ] 2.4 Ensure app starts with DATABASE_URL, GOOGLE_CLIENT_ID, META_API_TOKEN from environment
- [ ] 2.5 Add Prometheus client library to requirements.txt (prometheus-client)

## 3. Health Check Endpoints (HU-028)

- [ ] 3.1 Implement GET /health endpoint (returns 200 + JSON metadata + dependency statuses)
- [ ] 3.2 Implement GET /ready endpoint (returns 200 only if Postgres + Gemini healthy)
- [ ] 3.3 Add Postgres health probe (connection pool test query)
- [ ] 3.4 Add Gemini API health probe (timeout 5s, text generation test)
- [ ] 3.5 Add EspoCRM health probe (timeout 5s, call health endpoint if available)
- [ ] 3.6 Add Firebird health probe (timeout 3s, connection test)
- [ ] 3.7 Test health endpoints locally: `curl http://localhost:8000/health` and `/ready`
- [ ] 3.8 Verify timeout handling (no hung probes)

## 4. Prometheus Metrics Instrumentation

- [ ] 4.1 Add Prometheus client library initialization in main.py (create REGISTRY)
- [ ] 4.2 Create http_request_duration_seconds histogram (labels: method, endpoint, status)
- [ ] 4.3 Create http_requests_total counter (labels: method, endpoint, status)
- [ ] 4.4 Create exceptions_total counter (labels: type)
- [ ] 4.5 Create external_service_latency_seconds histogram (labels: service, operation, status)
- [ ] 4.6 Create app_uptime_seconds gauge
- [ ] 4.7 Create dependency_health_status gauge (labels: dependency)
- [ ] 4.8 Add middleware/decorator to instrument all endpoints
- [ ] 4.9 Implement GET /metrics endpoint (returns Prometheus metrics)
- [ ] 4.10 Test metrics endpoint: `curl http://localhost:8000/metrics`

## 5. Nginx Configuration (HU-026, nginx reverse proxy)

- [ ] 5.1 Create nginx.conf (or nginx/default.conf) in repo
- [ ] 5.2 Configure upstream to Gunicorn (http://app:8000)
- [ ] 5.3 Configure rate limiting zone (limit_req_zone with 10 req/min per IP)
- [ ] 5.4 Apply rate limiting to /agentes/liberar location
- [ ] 5.5 Enable gzip compression (text/html, application/json, etc.)
- [ ] 5.6 Add security headers (HSTS, X-Frame-Options, X-Content-Type-Options, CSP)
- [ ] 5.7 Configure access/error logging
- [ ] 5.8 Test nginx config: `docker-compose -f docker-compose.prod.yml up` and verify proxy works
- [ ] 5.9 Test rate limiting: curl requests to /agentes/liberar from single IP, expect 429 after 10/min

## 6. GitHub Actions CI/CD Pipeline (HU-027)

- [ ] 6.1 Create .github/workflows/deploy.yml file
- [ ] 6.2 Define trigger: push to any branch for test stage, push to main for deploy stage
- [ ] 6.3 Test stage: checkout → pip install -r requirements.txt → pytest --cov (>70% gate) → bandit SAST
- [ ] 6.4 Build stage: docker build -t demobot:latest -t demobot:$GITHUB_SHA .
- [ ] 6.5 Push stage: authenticate to Docker Hub/ECR → push both tags
- [ ] 6.6 Deploy stage (main only): pull image → docker run with env vars → health check probe
- [ ] 6.7 Add GitHub Secrets for registry auth (DOCKER_USERNAME, DOCKER_PASSWORD)
- [ ] 6.8 Test workflow: push feature branch → verify test/build/push run, deploy skipped
- [ ] 6.9 Test main deploy: push to main → verify full pipeline including deploy

## 7. Prometheus & Monitoring Stack (docker-compose)

- [ ] 7.1 Add prometheus service to docker-compose.prod.yml
- [ ] 7.2 Create prometheus.yml config (scrape_configs with target: app:8000/metrics)
- [ ] 7.3 Set scrape_interval to 15s
- [ ] 7.4 Add prometheus rules file for alerting (latency > 3s, error_rate > 1%, uptime)
- [ ] 7.5 Add Grafana service to docker-compose.prod.yml
- [ ] 7.6 Create Grafana dashboard JSON (panels: latency, error_rate, uptime, dependency health)
- [ ] 7.7 Configure Grafana provisioning (auto-provision dashboard on startup)
- [ ] 7.8 Test monitoring: docker-compose up → access Grafana at localhost:3000, verify metrics appear

## 8. Secrets & Environment Configuration

- [ ] 8.1 Update .env.example with all required env vars (DATABASE_URL, GOOGLE_*, META_*, FIREBIRD_*)
- [ ] 8.2 Ensure app never logs secrets (audit logging middleware)
- [ ] 8.3 Configure docker-compose.prod.yml to pull secrets from .env or separate volume
- [ ] 8.4 Test: start container with env vars, verify no secrets in logs
- [ ] 8.5 Document secret rotation runbook

## 9. Integration Testing (Smoke Tests)

- [ ] 9.1 Create smoke test script: curl /health, /ready, /metrics endpoints
- [ ] 9.2 Test full journey: make webhook request → verify 200, latency < 3s
- [ ] 9.3 Test rate limiting: 11 requests to /agentes/liberar in 60s → expect 429
- [ ] 9.4 Test error handling: kill Postgres → /health returns error for postgres, /ready returns 503
- [ ] 9.5 Run tests against local docker-compose.prod.yml
- [ ] 9.6 Document: "How to run smoke tests locally"

## 10. Lead Notifications (OPTIONAL, HU-021, SHOULD priority)

- [ ] 10.1 Add APScheduler to requirements.txt
- [ ] 10.2 Implement lead collection (new_leads table/query in memory or DB)
- [ ] 10.3 Implement scheduler job (runs daily at configured time, e.g., 8am)
- [ ] 10.4 Implement email sending to LEADS_EMAIL (use Gmail or SendGrid)
- [ ] 10.5 Handle retry on email failure (3 retries + log)
- [ ] 10.6 Ensure no duplicate emails sent (track sent leads by timestamp)
- [ ] 10.7 Test: trigger leads → wait for scheduler → verify email received
- [ ] 10.8 Document: "How to configure lead notification schedule and email"

## 11. Documentation & Runbooks

- [ ] 11.1 Write README.md for deployment (prerequisites, environment setup, deployment steps)
- [ ] 11.2 Write runbook: "How to deploy" (git push → wait for Actions → verify health checks)
- [ ] 11.3 Write runbook: "How to rollback" (git revert → push → new deploy)
- [ ] 11.4 Write runbook: "How to debug" (check logs, health endpoints, Prometheus metrics)
- [ ] 11.5 Write runbook: "How to rotate secrets" (update env vars, redeploy)
- [ ] 11.6 Write operational guide: "Monitoring dashboard overview" (how to read Grafana)

## 12. Deployment Target Setup (out-of-band, manual)

- [ ] 12.1 Choose cloud provider (AWS ECS, DigitalOcean, Heroku, or self-hosted)
- [ ] 12.2 Create container registry account (Docker Hub or AWS ECR)
- [ ] 12.3 Create database (AWS RDS Postgres or equivalent)
- [ ] 12.4 Set up GitHub Secrets for deploy (registry auth, database URL, API keys)
- [ ] 12.5 Deploy image manually once (verify health checks pass in production)
- [ ] 12.6 Set up monitoring alerts (Grafana → email/Slack on alert fire)

**Note:** Tasks 12.x are manual setup outside of code; they happen after code CI/CD pipeline is ready.
