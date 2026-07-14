# Health Checks Specification

## ADDED Requirements

### Requirement: /health Endpoint
The system SHALL provide a `/health` endpoint that returns the status of the application and its dependencies.

#### Scenario: Endpoint is always available
- **WHEN** a GET request is made to `/health`
- **THEN** endpoint responds with 200 OK (even if dependencies are unhealthy)

#### Scenario: Response includes metadata
- **WHEN** GET /health is called
- **THEN** response is JSON with fields: status (string), timestamp (ISO 8601), uptime_seconds (integer), version (string)

#### Scenario: Response includes dependency status
- **WHEN** GET /health is called
- **THEN** response includes dependencies object with postgres (ok/degraded/error), gemini (ok/degraded/error), espocrm (ok/degraded/error), firebird (ok/degraded/error)

#### Scenario: Postgres dependency probe
- **WHEN** /health is called and Postgres is reachable
- **THEN** postgres status is "ok"; if unreachable (timeout 3s), status is "error"

#### Scenario: Gemini API dependency probe
- **WHEN** /health is called
- **THEN** workflow calls Gemini with short test prompt (timeout 5s); if success, status "ok"; if timeout/error, status "degraded"

#### Scenario: EspoCRM dependency probe
- **WHEN** /health is called
- **THEN** workflow checks EspoCRM health endpoint (timeout 5s); if 200 OK, status "ok"; otherwise "degraded"

#### Scenario: Firebird dependency probe
- **WHEN** /health is called
- **THEN** workflow attempts Firebird connection (timeout 3s); if success, status "ok"; otherwise "error"

### Requirement: /ready Endpoint
The system SHALL provide a `/ready` endpoint that returns 200 OK only if all critical dependencies are healthy.

#### Scenario: Ready when all healthy
- **WHEN** all dependencies (Postgres, Gemini, EspoCRM, Firebird) are healthy
- **THEN** GET /ready returns 200 OK

#### Scenario: Not ready when dependencies unhealthy
- **WHEN** Postgres is unreachable or Gemini is timing out
- **THEN** GET /ready returns 503 Service Unavailable

#### Scenario: Readiness used by load balancer
- **WHEN** container starts
- **THEN** load balancer probes /ready every 10s; only routes traffic to container if /ready returns 200

#### Scenario: Graceful degradation
- **WHEN** a non-critical dependency (EspoCRM) is slow but Postgres and Gemini healthy
- **THEN** /ready returns 200 (Postgres + Gemini sufficient); /health shows espocrm as "degraded"

### Requirement: Health Check Latency
The system SHALL respond to health checks quickly to avoid false negatives.

#### Scenario: /health responds in < 1 second
- **WHEN** GET /health is called
- **THEN** response time is < 1 second (measured from request to response complete)

#### Scenario: /ready responds in < 1 second
- **WHEN** GET /ready is called
- **THEN** response time is < 1 second

### Requirement: Dependency Probe Timeouts
The system SHALL timeout external service probes to prevent hanging.

#### Scenario: Postgres probe timeout
- **WHEN** Postgres is hanging (no response)
- **THEN** probe times out after 3 seconds, status "error", /health returns without blocking

#### Scenario: Gemini probe timeout
- **WHEN** Gemini API is unreachable or hanging
- **THEN** probe times out after 5 seconds, status "degraded", /health returns without blocking

#### Scenario: EspoCRM probe timeout
- **WHEN** EspoCRM endpoint is unreachable
- **THEN** probe times out after 5 seconds, status "degraded", /health returns without blocking
