import pytest
from datetime import datetime
from agent.db import Contacto, Conversacion, Radicado
from agent.memory import Mensaje, abrir_conversacion, cerrar_conversacion, guardar_mensaje, obtener_historial

@pytest.mark.asyncio
async def test_contacto_tiene_consentimiento():
    contacto = Contacto(telefono="1234567890", nombre="Test", consentimiento_datos=True)
    assert contacto.consentimiento_datos is True

@pytest.mark.asyncio
async def test_crear_conversacion():
    conv = Conversacion(id=1, telefono="1234567890", estado="abierta")
    assert conv.telefono == "1234567890"
    assert conv.estado == "abierta"
    assert hasattr(conv, 'radicado_id')

@pytest.mark.asyncio
async def test_mensaje_ligado_a_conversacion():
    msg = Mensaje(id=1, conversacion_id=1, role="user", content="Hola")
    assert msg.conversacion_id == 1

from unittest.mock import patch, AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_abrir_y_cerrar_conversacion_helper():
    # Mock db interactions directly to avoid connection refused
    mock_session = AsyncMock()
    # Mock the context manager __aenter__ to return the mock session
    
    with patch("agent.memory.SessionLocal") as mock_session_cls:
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        
        # Mock refresh
        async def mock_refresh(obj):
            obj.id = 1
        mock_session.refresh.side_effect = mock_refresh
        
        conv_id = await abrir_conversacion("1234567890")
        assert conv_id == 1
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called()

        # Mock execute for select
        mock_result = MagicMock()
        mock_conv = Conversacion(id=1, telefono="1234567890", estado="abierta")
        mock_result.scalars().first.return_value = mock_conv
        mock_session.execute.return_value = mock_result
        
        cerrado = await cerrar_conversacion(1)
        assert cerrado is True
        assert mock_conv.estado == "cerrada"
