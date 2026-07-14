# EP-005-MINI: Design — Production Deployment Stack

## Context

Current state: Application runs in dev environment (`docker-compose.yml` local, manual docker build/run, tests via pytest). No automation, no production infrastructure, no health checks.

Target: v1.0 public demo must be deployable to cloud with 99% uptime SLA, <500ms response time, automated test→build→deploy pipeline, health probes, and operational runbooks.

Constraints:
- Demo = single instance (no HA/scaling for v1.0)
- Team: 1-2 backend engineers, limited DevOps expertise
- Budget: Cloud cost <$100/month (t3.micro → t3.small instance class)
- Timeline: 3-4 days to MVP (Dockerization + CI/CD + health checks)

## Goals / Non-Goals

**Goals:**
- Reproducible, versioned deployment pipeline (git push → auto-deploy)
- Health checks (`/health`, `/ready`) with dependency probes (Postgres, Gemini, EspoCRM)
- Production-ready Dockerfile (multi-stage, minimal image size <500MB)
- Prometheus metrics collection and alerting for latency, error rate, uptime
- Rate limiting on webhook to prevent abuse (10 req/min per IP)
- Rollback capability (git revert + re-deploy, <5 min)
- Monitoring dashboard (Grafana template for ops team)

**Non-Goals:**
- Kubernetes or orchestration (v1.0: managed Docker on AWS ECS or similar, v1.1 candidate)
- Full encryption at rest (DB already in VPC, acceptable for demo)
- Auto-scaling or HA (single instance sufficient for <100 concurrent users)
- Compliance audits (SOC2, GDPR; deferred to v1.1 if needed)
- Custom load testing framework (use cloud LB native testing tools)

## Decisions

### 1. Web Server: Gunicorn + Nginx (not uWSGI, not Uvicorn standalone)
**Why:** Gunicorn is battle-tested, supports multi-worker mode, plays well with Nginx. Uvicorn alone lacks reverse proxy features (rate limiting, compression). uWSGI adds complexity we don't need.

**Rationale:** Nginx + Gunicorn is the standard Python web stack. Minimal operational overhead vs bespoke solutions.

**Alternatives considered:**
- uWSGI: more features, steeper learning curve, harder to debug
- Uvicorn standalone: simpler, but loses reverse proxy benefits (rate limiting, compression, header manipulation)

### 2. Database: Cloud-managed PostgreSQL (AWS RDS) vs self-hosted
**Why:** Cloud-managed for v1.0 (RDS handles backups, failover, patches automatically). Reduces operational burden.

**Decision:** RDS Postgres 14+ (or equivalent on GCP Cloud SQL, Azure). Self-hosted postgres in Docker container is acceptable as fallback if Cloud Postgres not available during demo.

**Trade-off:** Higher cost (~$30/month RDS micro) vs operational simplicity. Acceptable for v1.0 demo.

### 3. CI/CD: GitHub Actions (not Jenkins, not GitLab CI)
**Why:** Already in GitHub, free tier covers demo, no infrastructure to maintain.

**Pipeline:**
```
trigger: git push to main
stage 1 (test):     checkout → pip install → pytest --cov (>70%) → bandit (SAST)
stage 2 (build):    docker build → tag → push to ECR (or Docker Hub)
stage 3 (deploy):   pull image → docker run + health check probe → mark deployed
stage 4 (monitor):  Prometheus scrape + Grafana alert if down
```

### 4. Monitoring: Prometheus + Grafana (not CloudWatch-only, not Datadog)
**Why:** Open-source, self-hosted in Docker, metrics collected via Prometheus client library in Python.

**Metrics collected:**
- Bot latency (p50, p95, p99)
- Webhook rate limiting hits (10 req/min enforcement)
- External service latency (Gemini, Google Calendar, EspoCRM, Firebird)
- Error rate by endpoint + by service
- Uptime (from `/health` probes)

**Dashboard:** Grafana template pre-configured with key panels. Alerts: if latency > 3s or error_rate > 1%, notify ops.

### 5. Health Checks: Passive + Active Probes
**Why:** Load balancer (or ops) probes `/health` every 10s. App responds with status of dependencies.

**Endpoints:**
- `GET /health` → 200 OK + JSON (status, uptime, dependencies status)
- `GET /ready` → 200 OK only if all dependencies healthy (used by LB for traffic routing)

**Dependency probes:**
- PostgreSQL: connection pool test query
- Gemini API: short text generation (timeout 5s)
- EspoCRM: API health endpoint (timeout 5s)
- Firebird: connection test (timeout 3s)

### 6. Rate Limiting: Nginx per-IP (not app-level, not Redis-backed)
**Why:** Nginx enforces at ingress, simple, no distributed state required for v1.0.

**Config:**
```nginx
limit_req_zone $binary_remote_addr zone=webhook_limit:10m rate=10r/m;
location /agentes/liberar {
  limit_req zone=webhook_limit burst=2 nodelay;
  proxy_pass http://gunicorn;
}
```

**Trade-off:** Only works for single-instance. If scaling to multiple instances in v1.1, migrate to Redis-backed rate limiting.

### 7. Secrets: Environment Variables (not .env file in image)
**Why:** Secrets (DB_URL, GOOGLE_*, META_*) passed via environment at runtime, not baked into Docker image.

**Mechanism:**
- Docker: `docker run -e DATABASE_URL=$DB_URL ...`
- GitHub Actions: Secrets stored in repo settings, injected into deploy job
- Cloud: Container orchestration (ECS, etc.) pulls from Secrets Manager

### 8. Deployment Target: AWS ECS or DigitalOcean App Platform (not Heroku)
**Why:** Cost-effective ($20-50/month for t3.micro), full control, integrates with GitHub Actions.

**Fallback:** Docker image pushed to Docker Hub; anyone can `docker run` locally (for demo purposes).

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Single instance failure** | 100% downtime | Alerting on `/health` probes; runbook for manual restart (5 min RTO) |
| **Database connection leak** | Postgres max connections hit, bot hangs | Connection pool size tuning (HikariCP-equivalent in SQLAlchemy); health check probes for connection pool exhaustion |
| **Cold start latency** | First request after deploy slow | Pre-warm connections on startup; health check delay (30s) before accepting traffic |
| **GitHub Actions outage** | Can't deploy | Manual docker push + run fallback (documented in runbook) |
| **Secrets rotation** | If API key compromised, must redeploy | Runbook for rotating secrets + immediate re-deploy via Actions |
| **Image size bloat** | Slow pulls, higher compute cost | Multi-stage Dockerfile enforces <500MB limit; monthly audit |

## Migration Plan

### Phase 1: Local Validation (Day 1-2)
1. Write Dockerfile (multi-stage)
2. Test locally: `docker build` + `docker run` against local postgres + mock Gemini
3. Write docker-compose.prod.yml (Gunicorn, Nginx, Postgres, Prometheus)
4. Validate health checks locally

### Phase 2: CI/CD Setup (Day 2-3)
1. Write `.github/workflows/deploy.yml` (test → build → push image)
2. Set up Docker registry (ECR, Docker Hub, or cloud-native)
3. Test full pipeline: push branch → GitHub Actions runs → image built and pushed
4. Set up AWS ECS task definition or DigitalOcean App Platform config

### Phase 3: Deploy to Staging (Day 3-4)
1. Deploy image to staging environment (ECS task or App Platform)
2. Run smoke tests against staging (health checks, webhook hits)
3. Validate Prometheus scraping and Grafana dashboard
4. Document runbooks: deploy, rollback, scale, debug

### Phase 4: Go Live (Day 4-5)
1. Deploy to production environment
2. Set up alerting (latency, error rate, uptime)
3. On-call handoff and runbook training

### Rollback Strategy
- If deploy breaks prod: `git revert <commit>` → push → GitHub Actions auto-deploys previous image
- Time to rollback: <5 minutes (assuming image already cached in registry)

## Open Questions

1. **Cloud provider choice:** AWS ECS vs DigitalOcean vs Heroku vs self-hosted? (Cost + operational complexity trade-off)
2. **Monitoring SLA:** Who monitors Prometheus/Grafana during demo? (Assumes ops-aware audience for now)
3. **Data persistence:** Keep demo database state across redeploys, or reset on each deploy? (Recommend reset for cleanliness)
4. **Secrets management:** GitHub Secrets sufficient for demo, or migrate to AWS Secrets Manager / Vault? (GitHub Secrets for v1.0)
5. **Performance baseline:** Before load testing, establish baseline latency for each service (Gemini, Google Calendar, EspoCRM). Targets in HU-028 are aggressive (<500ms E2E). Feasible?
