# monitoring-alerting Specification

## Purpose
TBD - created by archiving change ep-005-mini. Update Purpose after archive.
## Requirements
### Requirement: Prometheus Metrics Instrumentation
The system SHALL collect key metrics and expose them in Prometheus format.

#### Scenario: Metrics endpoint available
- **WHEN** a GET request is made to `/metrics`
- **THEN** endpoint returns Prometheus-formatted metrics (text/plain format with HELP and TYPE headers)

#### Scenario: Latency metrics
- **WHEN** requests are processed
- **THEN** histogram metrics track latency: http_request_duration_seconds (labels: method, endpoint, status) with buckets [.01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10]

#### Scenario: Error rate metrics
- **WHEN** requests fail or exceptions occur
- **THEN** counter metrics track: http_requests_total (labels: method, endpoint, status), exceptions_total (labels: type), tool_errors_total (labels: tool_name, error_type)

#### Scenario: External service latency metrics
- **WHEN** calls to Gemini, Google Calendar, EspoCRM, Firebird occur
- **THEN** histogram metrics track: external_service_latency_seconds (labels: service, operation, status)

#### Scenario: Uptime metric
- **WHEN** application is running
- **THEN** gauge metric: app_uptime_seconds tracks seconds since application started

#### Scenario: Dependency health metrics
- **WHEN** /health probes run (on every /health call or periodic)
- **THEN** gauge metrics: dependency_health_status (labels: dependency) with values 1 (ok), 0.5 (degraded), 0 (error)

### Requirement: Prometheus Scraping Configuration
The system SHALL configure Prometheus to scrape metrics.

#### Scenario: Prometheus service included in docker-compose.prod.yml
- **WHEN** docker-compose prod stack starts
- **THEN** Prometheus service (prometheus:latest) is orchestrated with proper configuration

#### Scenario: Prometheus scrape job
- **WHEN** Prometheus starts
- **THEN** scrape_configs includes target: localhost:8000/metrics (or app service endpoint) with scrape_interval 15s

#### Scenario: Metrics are queryable
- **WHEN** Prometheus UI is accessed (localhost:9090 in prod stack)
- **THEN** metrics are available for query after first scrape (within 15s of app startup)

### Requirement: Grafana Dashboard
The system SHALL provide a pre-built Grafana dashboard for operational monitoring.

#### Scenario: Grafana service in compose
- **WHEN** docker-compose prod stack starts
- **THEN** Grafana service (grafana:latest) is orchestrated, accessible at localhost:3000

#### Scenario: Dashboard displays key metrics
- **WHEN** Grafana dashboard is opened
- **THEN** displays panels: P50/P95/P99 latency, error rate, uptime, dependency health, external service latencies

#### Scenario: Dashboard is pre-configured
- **WHEN** Grafana starts
- **THEN** dashboard is auto-provisioned from config file (no manual setup required)

### Requirement: Alerting Rules
The system SHALL define and trigger alerts for critical conditions.

#### Scenario: Latency alert
- **WHEN** P99 latency (http_request_duration_seconds) exceeds 3 seconds for 5 minutes
- **THEN** alert "HighLatency" is triggered, visible in Prometheus alerts

#### Scenario: Error rate alert
- **WHEN** error rate (errors / total requests) exceeds 1% for 5 minutes
- **THEN** alert "HighErrorRate" is triggered

#### Scenario: Uptime alert
- **WHEN** app_uptime_seconds metric is missing for > 1 minute (app crashed/restarted)
- **THEN** alert "InstanceDown" is triggered

#### Scenario: Dependency health alert
- **WHEN** dependency_health_status drops to 0 (error) for Postgres or Gemini
- **THEN** alert "CriticalDependencyDown" is triggered

### Requirement: Alerting Delivery
The system SHALL notify operators when alerts fire.

#### Scenario: Alert log output
- **WHEN** alerts fire
- **THEN** alerts are logged to stdout/stderr (for ops visibility in container logs)

#### Scenario: Webhook integration (optional)
- **WHEN** configured with Alertmanager webhook
- **THEN** alerts are POSTed to specified endpoint (e.g., Slack, PagerDuty) for notification

### Requirement: Metrics Retention
The system SHALL retain metrics for troubleshooting.

#### Scenario: Prometheus retention
- **WHEN** Prometheus service runs
- **THEN** retains metrics for 30 days (default) or as configured via --storage.tsdb.retention.time

