"""Shared test fixtures for agent tests."""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Load test environment before importing agent modules
env_test = Path(__file__).parent.parent / ".env.test"
if env_test.exists():
    load_dotenv(env_test)


@pytest.fixture
def mock_gemini():
    """Mock Gemini API client."""
    mock = AsyncMock()
    mock.generate_content = AsyncMock(
        return_value=Mock(text="Hola, soy un asistente. ¿Cómo puedo ayudarte?")
    )
    return mock


@pytest.fixture
def mock_google_calendar():
    """Mock Google Calendar API."""
    mock = MagicMock()
    mock.horarios_libres = Mock(
        return_value=[
            {"start": "09:00", "end": "10:00", "date": "2026-07-15"},
            {"start": "14:00", "end": "15:00", "date": "2026-07-15"},
        ]
    )
    mock.crear_evento_calendar = Mock(
        return_value={"event_id": "abc123", "link": "https://meet.google.com/abc"}
    )
    return mock


@pytest.fixture
def mock_espocrm():
    """Mock EspoCRM API."""
    mock = MagicMock()
    mock.crear_caso = Mock(
        return_value={"case_id": "CASE-001", "status": "Nuevo"}
    )
    mock.obtener_cliente = Mock(
        return_value={"id": "CL-001", "nombre": "Acme Corp", "estado": "lead"}
    )
    return mock


@pytest.fixture
def mock_firebird():
    """Mock Firebird database."""
    mock = MagicMock()
    mock.consultar_licencia = Mock(
        return_value={"licencia_id": "LIC-001", "estado": "activa", "vencimiento": "2027-12-31"}
    )
    return mock


@pytest.fixture
def mock_postgres():
    """Mock Postgres connection."""
    mock = MagicMock()
    mock.obtener_historial = Mock(
        return_value=[
            {"rol": "usuario", "contenido": "Hola", "timestamp": "2026-07-13T10:00:00Z"},
            {"rol": "bot", "contenido": "Hola, ¿cómo estás?", "timestamp": "2026-07-13T10:00:05Z"},
        ]
    )
    mock.guardar_mensaje = Mock(return_value=True)
    return mock


@pytest.fixture
def mock_meta_signature():
    """Mock Meta webhook signature validation."""
    def validate(body: str, signature: str, token: str = "test_token") -> bool:
        # Simple mock: valid signature is "valid_sig_<hash>"
        return signature == "valid_sig_abc123"
    return validate


@pytest.fixture
def mock_env(monkeypatch):
    """Set up test environment variables."""
    test_vars = {
        "GEMINI_API_KEY": "test_gemini_key",
        "GOOGLE_OAUTH_TOKEN": "test_google_token",
        "META_API_TOKEN": "test_meta_token",
        "META_PHONE_NUMBER_ID": "123456789",
        "META_VERIFY_TOKEN": "test_verify_token",
        "DATABASE_URL": "postgresql://test:test@localhost/test_db",
        "FIREBIRD_HOST": "localhost",
        "ISC_PASSWORD": "test_firebird",
        "EMAIL_SOPORTE": "soporte@test.com",
    }
    for key, value in test_vars.items():
        monkeypatch.setenv(key, value)
    return test_vars


@pytest.fixture
def sample_webhook_payload():
    """Sample Meta webhook payload."""
    return {
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
                                    "text": {"body": "Hola, quiero conocer vuestros planes"},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


@pytest.fixture
def sample_valid_signature():
    """Valid Meta webhook signature."""
    return "valid_sig_abc123"
