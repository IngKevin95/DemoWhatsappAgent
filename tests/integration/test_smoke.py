"""Smoke tests: end-to-end journey validation"""
import pytest
from unittest.mock import AsyncMock
from starlette.testclient import TestClient
from agent.main import app


@pytest.fixture(autouse=True)
def mock_health_probes(monkeypatch):
    """Los probes tocan infra real; mockearlos para validar el contrato del
    endpoint de forma determinista (no la conectividad real de la infra)."""
    for probe in ("probe_postgres", "probe_gemini", "probe_espocrm", "probe_firebird"):
        monkeypatch.setattr(f"agent.main.{probe}", AsyncMock(return_value="ok"))


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


class TestWebhookJourney:
    """End-to-end webhook journey smoke tests"""

    def test_health_check_accessible(self, client):
        """Smoke: Health endpoint accessible"""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert 'dependencies' in data

    def test_ready_check_accessible(self, client):
        """Smoke: Ready endpoint accessible"""
        response = client.get('/ready')
        assert response.status_code == 200
        data = response.json()
        assert data['ready'] is True

    def test_metrics_accessible(self, client):
        """Smoke: Metrics endpoint accessible"""
        response = client.get('/metrics')
        assert response.status_code == 200
        assert 'http_requests_total' in response.text

    def test_root_endpoint_accessible(self, client):
        """Smoke: Root endpoint accessible"""
        response = client.get('/')
        assert response.status_code == 200
        data = response.json()
        assert 'status' in data

    def test_health_endpoints_latency_acceptable(self, client):
        """Smoke: Health endpoints respond in reasonable time"""
        import time

        # Time health endpoint
        start = time.time()
        response = client.get('/health')
        latency_ms = (time.time() - start) * 1000

        assert response.status_code == 200
        assert latency_ms < 1000  # Must respond in < 1 second

        # Time ready endpoint
        start = time.time()
        response = client.get('/ready')
        latency_ms = (time.time() - start) * 1000

        assert response.status_code == 200
        assert latency_ms < 1000

    def test_health_uptime_tracking_works(self, client):
        """Smoke: Health endpoint tracks uptime correctly"""
        response1 = client.get('/health')
        uptime1 = response1.json()['uptime_seconds']

        # Make another request
        response2 = client.get('/health')
        uptime2 = response2.json()['uptime_seconds']

        # Uptime should increase (or stay same)
        assert uptime2 >= uptime1

    def test_all_dependency_statuses_present(self, client):
        """Smoke: All expected dependencies reported in health"""
        response = client.get('/health')
        deps = response.json()['dependencies']

        expected_deps = ['postgres', 'gemini', 'espocrm', 'firebird']
        for dep in expected_deps:
            assert dep in deps, f"Missing dependency: {dep}"
            assert deps[dep] in ['ok', 'degraded', 'error']
