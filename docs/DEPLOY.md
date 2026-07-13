# Deployment Guide

## Prerequisites

- Docker & Docker Compose installed
- Git access to repository
- Environment variables configured in `.env`
- Database credentials ready

## Quick Deploy (Staging)

```bash
# Clone repo
git clone https://github.com/IngKevin95/DemoWhatsappAgent.git
cd DemoWhatsappAgent

# Copy and configure .env
cp .env.example .env
# Edit .env with staging values

# Build and start services
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Verify health (HTTP in dev, HTTPS in prod with certificates)
curl http://localhost/health
curl http://localhost/ready

# Check logs
docker-compose -f docker-compose.prod.yml logs -f app
```

## GitHub Secrets (Required for CI/CD)

Configure these in GitHub repository Settings → Secrets and Variables → Actions:

```
STAGING_SSH_KEY         # Private SSH key for staging server (base64 encoded)
STAGING_USER            # SSH user for staging (e.g., deploy)
STAGING_HOST            # Staging server hostname or IP
PRODUCTION_SSH_KEY      # Private SSH key for production server (base64 encoded)
PRODUCTION_USER         # SSH user for production (e.g., deploy)
PRODUCTION_HOST         # Production server hostname or IP
```

## Production Deploy (CI/CD)

1. **Merge to main branch** → triggers GitHub Actions
2. **Test stage** runs (pytest, coverage > 70%, bandit SAST)
3. **Build stage** creates Docker image, pushes to GHCR
4. **Deploy stage** (main only):
   - SSH to production server using secrets
   - Pull latest image
   - Restart services with `docker-compose -f docker-compose.prod.yml up -d`
   - Verify health checks pass (HTTPS)

## Manual Deploy Steps

```bash
# 1. SSH to production
ssh -i ~/.ssh/production_key user@prod-server

# 2. Navigate to app directory
cd /opt/demobot

# 3. Pull latest code
git pull origin main

# 4. Update .env if needed
nano .env

# 5. Rebuild services
docker-compose -f docker-compose.prod.yml build

# 6. Apply database migrations (if any)
docker-compose -f docker-compose.prod.yml exec app python -m alembic upgrade head

# 7. Restart services
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# 8. Monitor startup logs
docker-compose -f docker-compose.prod.yml logs -f app nginx

# 9. Health check (production uses HTTPS)
curl -f https://localhost/health || echo "Health check failed"

# 10. Verify metrics
curl https://localhost/metrics | head -20

## SSL/TLS Certificate Setup

For production HTTPS (required for Meta webhook callback):

1. **Obtain certificates** (Let's Encrypt recommended):
   ```bash
   certbot certonly --standalone -d api.yourdomain.com
   ```

2. **Copy to server**:
   ```bash
   scp -i ~/.ssh/production_key /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem \
       user@prod-server:/opt/demobot/nginx_certs/cert.pem
   scp -i ~/.ssh/production_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem \
       user@prod-server:/opt/demobot/nginx_certs/key.pem
   ```

3. **Verify nginx sees them**:
   ```bash
   docker-compose -f docker-compose.prod.yml exec nginx test -f /etc/nginx/certs/cert.pem
   ```

4. **Restart nginx**:
   ```bash
   docker-compose -f docker-compose.prod.yml restart nginx
   ```
```

## Rollback

See [ROLLBACK.md](./ROLLBACK.md)

## Monitoring

- **Grafana**: http://localhost:3000 (admin / check .env)
- **Prometheus**: http://localhost:9090
- **App Metrics**: http://localhost/metrics
- **Logs**: `docker-compose logs -f app`
