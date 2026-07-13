"""Additional tests for main.py to increase coverage."""

import pytest
from unittest.mock import patch, AsyncMock
from agent.main import root, enviar_mensaje_seguro, _segundos_desde
from datetime import datetime, timezone, timedelta


def test_root_endpoint():
    """Root endpoint returns status."""
    from agent.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "status" in response.json()


@pytest.mark.asyncio
async def test_enviar_mensaje_seguro():
    """enviar_mensaje_seguro handles errors gracefully."""
    with patch('agent.main.proveedor') as mock_prov:
        mock_prov.enviar_mensaje = AsyncMock(side_effect=Exception("API error"))
        # Should not raise, handles exception gracefully
        await enviar_mensaje_seguro("34912345678", "Test")


def test_segundos_desde():
    """_segundos_desde calculates time difference."""
    now = datetime.now(timezone.utc)
    past = now - timedelta(seconds=60)
    segundos = _segundos_desde(past)
    assert segundos >= 59
    assert segundos <= 61
