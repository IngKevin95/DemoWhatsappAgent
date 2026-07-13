# Rollback Guide

## Quick Rollback

If deployment causes issues:

```bash
# SSH to production
ssh -i ~/.ssh/production_key user@prod-server
cd /opt/demobot

# Revert to previous commit
git revert HEAD
git push origin main

# Or reset to previous tag/commit
git checkout v1.0.5
git push origin main --force  # Only if absolutely necessary

# Restart services
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Verify health
curl -f http://localhost/health
```

## Step-by-Step Rollback

1. **Identify issue** from logs:
   ```bash
   docker-compose logs -f app | grep ERROR
   ```

2. **Check metrics** in Prometheus/Grafana:
   - Error rate spike?
   - Latency increase?
   - Dependency down?

3. **Stop services**:
   ```bash
   docker-compose -f docker-compose.prod.yml down
   ```

4. **Restore previous version**:
   ```bash
   git log --oneline | head -5
   git checkout <previous-commit>
   ```

5. **Rebuild and restart**:
   ```bash
   docker-compose -f docker-compose.prod.yml build
   docker-compose -f docker-compose.prod.yml up -d
   ```

6. **Verify health** (wait 30 seconds for startup):
   ```bash
   sleep 30
   curl -f http://localhost/health
   curl -f http://localhost/ready
   ```

## Database Rollback

If database migration failed:

```bash
# Check migration history
docker-compose exec app python -m alembic history

# Downgrade to previous version
docker-compose exec app python -m alembic downgrade -1

# Verify schema
docker-compose exec db psql -U demobot -d demowhatsapp -c "\dt"
```

## Notify Team

```bash
# Send Slack notification
curl -X POST $SLACK_WEBHOOK -d '{
  "text": "ROLLBACK: Reverted to v1.0.5 due to [issue description]"
}'
```
