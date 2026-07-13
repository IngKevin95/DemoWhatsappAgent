# Containerization Specification

## ADDED Requirements

### Requirement: Docker Multi-Stage Build
The system SHALL provide a Dockerfile that uses multi-stage builds to separate build-time dependencies from runtime, resulting in a minimal production image.

#### Scenario: Build stage includes dependencies and tests
- **WHEN** `docker build` is executed with Dockerfile
- **THEN** build stage installs Python 3.11+, dependencies from requirements.txt, copies application code, and runs `pytest --cov` as a CI gate

#### Scenario: Runtime stage is minimal
- **WHEN** docker build completes
- **THEN** runtime stage uses Alpine or Debian slim base, contains only Python runtime + application code, size < 500MB, and includes health check configuration

#### Scenario: Image is deployable
- **WHEN** image is built
- **THEN** `docker run <image>` starts the application, exposes port 8000, and includes ENTRYPOINT for Gunicorn

### Requirement: Production Compose Configuration
The system SHALL provide docker-compose.prod.yml for local production-like environment testing.

#### Scenario: Compose includes all services
- **WHEN** `docker-compose -f docker-compose.prod.yml up` is executed
- **THEN** orchestrates: Gunicorn (app), Nginx (reverse proxy), PostgreSQL (db), Prometheus (monitoring)

#### Scenario: Services are isolated in network
- **WHEN** services start
- **THEN** each service runs in its own container, connected via named network (app_network), port 80/443 exposed via Nginx only

#### Scenario: Health checks are configured
- **WHEN** services start
- **THEN** each service (app, db, prometheus) includes health check configuration (interval 30s, timeout 10s, retries 3)

### Requirement: Environment Variable Configuration
The system SHALL accept all secrets and configuration via environment variables (not hardcoded, not .env in image).

#### Scenario: Database connection via env var
- **WHEN** container starts with DATABASE_URL environment variable
- **THEN** application connects to specified PostgreSQL instance

#### Scenario: API credentials via env vars
- **WHEN** container starts with GOOGLE_CLIENT_ID, META_API_TOKEN, FIREBIRD_HOST environment variables
- **THEN** application uses provided credentials for external service calls

#### Scenario: Secrets not in logs
- **WHEN** an exception occurs
- **THEN** exception logs do not contain DATABASE_URL, GOOGLE_*, META_*, FIREBIRD_* values (scrubbed)
