"""Prometheus metrics initialization and exports"""
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest

# Create default registry
registry = CollectorRegistry()

# HTTP Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint', 'status'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=registry
)

# Application Metrics
demobot_uptime_seconds = Gauge(
    'demobot_uptime_seconds',
    'Application uptime in seconds',
    registry=registry
)

demobot_active_conversations = Gauge(
    'demobot_active_conversations',
    'Number of active conversations',
    registry=registry
)

demobot_errors_total = Counter(
    'demobot_errors_total',
    'Total application errors',
    ['error_type'],
    registry=registry
)

demobot_tool_calls_total = Counter(
    'demobot_tool_calls_total',
    'Total tool/function calls',
    ['tool_name', 'status'],
    registry=registry
)

demobot_rate_limit_triggers_total = Counter(
    'demobot_rate_limit_triggers_total',
    'Total rate limit triggers',
    ['endpoint'],
    registry=registry
)

# Dependency Health
demobot_dependency_health = Gauge(
    'demobot_dependency_health',
    'Dependency health status (1=ok, 0.5=degraded, 0=error)',
    ['dependency'],
    registry=registry
)


def get_metrics():
    """Generate Prometheus metrics in text format"""
    return generate_latest(registry)
