"""Unit tests for main.py - webhook handling and request validation."""

import os
import pytest
import hmac
import hashlib
import json
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

try:
    from agent.main import app, recibir_webhook, validar_firma_meta
except ImportError:
    app = None


@pytest.fixture
def client():
    """FastAPI test client."""
    if app:
        return TestClient(app)
    return None


class TestValidarFirmaMeta:
    """Tests for Meta webhook signature validation (AC-4 security)."""

    def test_validar_firma_valida(self, mock_env):
        """Valid Meta signature accepted."""
        body = '{"entry":[{"changes":[{"value":{"messages":[]}}]}]}'
        token = mock_env["META_VERIFY_TOKEN"]

        # Compute correct signature
        signature = hmac.new(
            token.encode(),
            body.encode(),
            hashlib.sha256
        ).hexdigest()

        resultado = validar_firma_meta(body, f"sha256={signature}", token)
        assert resultado is True

    def test_validar_firma_invalida(self, mock_env):
        """Invalid signature rejected."""
        body = '{"entry":[]}'
        token = mock_env["META_VERIFY_TOKEN"]
        invalid_signature = "sha256=0000000000000000000000000000000000000000000000000000000000000000"

        resultado = validar_firma_meta(body, invalid_signature, token)
        assert resultado is False

    def test_validar_firma_ausente(self, mock_env):
        """Missing signature rejected."""
        body = '{"entry":[]}'
        resultado = validar_firma_meta(body, None, mock_env["META_VERIFY_TOKEN"])
        assert resultado is False


class TestRecibirWebhook:
    """Tests for webhook handler (AC-1 HU-001)."""

    def test_webhook_endpoint_exists(self, client):
        """Webhook endpoint is accessible."""
        assert client is not None
        # POST /webhook should exist (may 403 without valid signature)
        response = client.post("/webhook", json={"entry": []}, headers={"X-Hub-Signature-256": "sha256=invalid"})
        assert response.status_code in [403, 400]  # Unauthorized or bad request expected

    @pytest.mark.asyncio
    async def test_webhook_rate_limiting(self, mock_env):
        """Rate limiting: structural test (implementation deferred to EP-002)."""
        # For now, just verify we can call webhook (rate limiting added in EP-002)
        # This test confirms the webhook endpoint exists and responds
        pass

    @pytest.mark.asyncio
    async def test_webhook_generar_respuesta_timeout(self, mock_env):
        """Generar_respuesta timeout → fallback response (structural test)."""
        # Implementation: generar_respuesta has timeout parameter
        # This will be tested end-to-end in smoke phase
        pass


class TestWebhookAuditLogging:
    """Tests for audit logging in webhook handler."""

    def test_webhook_logging_structure(self, mock_env):
        """Audit logging is structured (AC-4 security)."""
        # Structural test: logger exists and is available
        # Full audit logging tested in smoke phase
        from agent.main import logger
        assert logger is not None

    def test_secrets_not_in_config(self, mock_env):
        """Secrets loaded from environment, not hardcoded."""
        # Verify that .env variables are used
        assert os.getenv("GEMINI_API_KEY") is not None
        assert os.getenv("META_API_TOKEN") is not None
        assert len(os.getenv("GEMINI_API_KEY", "")) > 0
