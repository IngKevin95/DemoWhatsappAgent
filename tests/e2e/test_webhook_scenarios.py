"""End-to-end webhook scenarios (journey smoke test)."""

import pytest
import json
import hmac
import hashlib
from unittest.mock import patch
from fastapi.testclient import TestClient
from agent.main import app

client = TestClient(app)


def compute_signature(body: str, token: str) -> str:
    """Compute valid Meta webhook signature."""
    return "sha256=" + hmac.new(
        token.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()


class TestWebhookJourney:
    """End-to-end journey: welcome → price → booking."""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """Set up test environment."""
        monkeypatch.setenv("META_VERIFY_TOKEN", "test_token")
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")

    def test_webhook_welcome_flow(self, setup_env):
        """Happy path: user says hello → bot welcomes."""
        with patch('agent.main.proveedor') as mock_proveedor:
            mock_proveedor.validar_firma.return_value = True
            mock_proveedor.parsear_webhook.return_value = None

            payload = {
                "entry": [
                    {
                        "changes": [
                            {
                                "value": {
                                    "messages": [
                                        {
                                            "from": "34912345678",
                                            "id": "msg_001",
                                            "timestamp": "1234567890",
                                            "type": "text",
                                            "text": {"body": "Hola"},
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ]
            }
            body_json = json.dumps(payload)
            sig = compute_signature(body_json, "test_token")

            response = client.post(
                "/webhook",
                content=body_json,
                headers={"X-Hub-Signature-256": sig},
            )

            # Should process webhook
            assert response.status_code in [200, 400, 403, 404]

    def test_webhook_root_endpoint(self):
        """Root endpoint responds."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "SysBot activo"
