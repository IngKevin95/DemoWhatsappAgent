# Debugging Guide

## Application Logs

```bash
# Tail app logs
docker-compose -f docker-compose.prod.yml logs -f app

# Search for errors
docker-compose logs app | grep ERROR

# Full log with timestamps
docker-compose logs app --timestamps
```

## Health Check Debugging

```bash
# Check /health endpoint
curl -v http://localhost/health

# Check /ready endpoint
curl -v http://localhost/ready

# Check each dependency status
curl http://localhost/health | jq '.dependencies'
```

## Metrics Debugging

```bash
# Get raw Prometheus metrics
curl http://localhost/metrics

# Check specific metric
curl http://localhost/metrics | grep http_requests_total

# Check if Prometheus is scraping
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {labels, lastScrape}'
```

## Database Debugging

```bash
# Connect to PostgreSQL
docker-compose -f docker-compose.prod.yml exec db psql -U demobot -d demowhatsapp

# Query active connections
SELECT pid, usename, application_name, state FROM pg_stat_activity;

# Check table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) 
FROM pg_tables ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

# Check recent messages
SELECT * FROM mensajes ORDER BY timestamp DESC LIMIT 10;
```

## Performance Profiling

```bash
# Generate CPU profile
docker-compose exec app python -m cProfile -o profile.stats agent/main.py

# Analyze profile
docker-compose cp app:/app/profile.stats .
python -m pstats profile.stats
```

## Network Debugging

```bash
# Check nginx access log
docker-compose logs nginx

# Verify upstream connectivity
docker-compose exec nginx curl -v http://app:8000/health

# Check rate limiting
docker-compose exec nginx nginx -T  # Validate config
```

## Container Debugging

```bash
# Interactive shell
docker-compose exec app bash

# Check environment
docker-compose exec app env | grep DATABASE_URL

# Check running processes
docker-compose exec app ps aux
```

## Common Issues

### App not starting
- Check logs: `docker-compose logs app`
- Verify environment: `docker-compose config | grep -A5 app:`
- Rebuild image: `docker-compose build --no-cache app`

### Database connection fails
- Verify DB is running: `docker-compose ps db`
- Check credentials in .env
- Test connection: `docker-compose exec db psql -U demobot -d demowhatsapp -c "SELECT 1"`

### Metrics not showing
- Check /metrics endpoint: `curl http://localhost/metrics`
- Verify Prometheus is scraping: `curl http://localhost:9090/api/v1/targets`
- Check prometheus.yml configuration

### High latency
- Check /metrics for request duration: `curl http://localhost/metrics | grep http_request_duration_seconds`
- Monitor CPU/Memory: `docker stats`
- Check database query performance: Enable slow query log
