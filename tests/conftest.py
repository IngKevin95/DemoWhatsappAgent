"""Shared test fixtures for agent tests."""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

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


@pytest.fixture(autouse=True)
def patch_db_connections(monkeypatch):
    """Patch all DB connections to prevent real connections in tests."""
    from unittest.mock import patch, AsyncMock, MagicMock

    # Patch memory.py async functions
    monkeypatch.setattr(
        "agent.memory.guardar_mensaje",
        AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        "agent.memory.obtener_historial",
        AsyncMock(return_value=[
            {"role": "usuario", "content": "Hola"},
            {"role": "bot", "content": "Hola, bienvenido"}
        ])
    )
    monkeypatch.setattr(
        "agent.memory.ultimo_mensaje",
        AsyncMock(return_value={"role": "bot", "content": "Test"})
    )
    monkeypatch.setattr(
        "agent.memory.ultimo_timestamp",
        AsyncMock(return_value=datetime.utcnow())
    )
    monkeypatch.setattr(
        "agent.memory.limpiar_historial",
        AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        "agent.memory.telefonos_con_actividad_reciente",
        AsyncMock(return_value=["34912345678"])
    )
    monkeypatch.setattr(
        "agent.memory.inicializar_db",
        AsyncMock(return_value=None)
    )

    # Patch tools.py functions that need DB
    def mock_consultar_precio(modulo):
        return {"modulo": modulo, "precio": 99.00, "moneda": "EUR"}

    def mock_consultar_licencia(identificacion):
        return {"licencia_id": "LIC-001", "estado": "activa", "vencimiento": "2027-12-31"}

    def mock_agendar_cita(**kwargs):
        return {"event_id": "EVT-001", "link": "https://meet.google.com/test", "status": "confirmada"}

    def mock_reclasificar_caso(**kwargs):
        return {"puede_procesar": True, "motivo": "Licencia valida"}

    def mock_escalar_a_humano(**kwargs):
        return {"agente_id": "AGENT-001", "area": "Soporte", "status": "escalado", "timestamp": datetime.utcnow()}

    def mock_consultar_disponibilidad(area):
        return [
            {"start": "09:00", "end": "10:00", "date": "2026-07-15"},
            {"start": "14:00", "end": "15:00", "date": "2026-07-15"}
        ]

    monkeypatch.setattr("agent.tools.consultar_precio_modulo", mock_consultar_precio)
    monkeypatch.setattr("agent.tools.consultar_licencia", mock_consultar_licencia)
    monkeypatch.setattr("agent.tools.agendar_cita", mock_agendar_cita)
    monkeypatch.setattr("agent.tools.reclasificar_caso_sin_licencia", mock_reclasificar_caso)
    monkeypatch.setattr("agent.tools.escalar_a_humano", mock_escalar_a_humano)
    monkeypatch.setattr("agent.tools.consultar_disponibilidad_agenda", mock_consultar_disponibilidad)
