"""Additional tests for main.py to increase coverage."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
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
    with patch('agent.main.proveedor_meta') as mock_prov:
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


@pytest.mark.asyncio
async def test_revisar_inactividad_sin_conversacion_activa():
    """_revisar_inactividad should do nothing if conv_id is None (closed conversation)."""
    from agent.main import _revisar_inactividad
    
    with patch("agent.main.telefonos_con_actividad_reciente", AsyncMock(return_value=["12345"])), \
         patch("agent.main.ultimo_mensaje", AsyncMock(return_value={"role": "user", "content": "hola", "timestamp": datetime.now(timezone.utc) - timedelta(seconds=1000)})), \
         patch("agent.main.obtener_conversacion_activa", AsyncMock(return_value=None)), \
         patch("agent.main.guardar_mensaje", AsyncMock()) as mock_guardar, \
         patch("agent.main.enviar_mensaje_seguro", AsyncMock()) as mock_enviar, \
         patch("asyncio.sleep", AsyncMock(side_effect=[None, ValueError("stop")])):
        
        try:
            await _revisar_inactividad()
        except ValueError:
            pass
            
        mock_guardar.assert_not_called()
        mock_enviar.assert_not_called()


@pytest.mark.asyncio
async def test_revisar_inactividad_ultimo_mensaje_usuario():
    """_revisar_inactividad sends CHECKIN_1 if last message is from user and timeout passed."""
    from agent.main import _revisar_inactividad, MENSAJE_CHECKIN_1
    
    mock_contacto = MagicMock()
    mock_contacto.canal = "telegram"
    
    with patch("agent.main.telefonos_con_actividad_reciente", AsyncMock(return_value=["12345"])), \
         patch("agent.main.ultimo_mensaje", AsyncMock(return_value={"role": "user", "content": "hola", "timestamp": datetime.now(timezone.utc) - timedelta(seconds=1000)})), \
         patch("agent.main.obtener_conversacion_activa", AsyncMock(return_value=42)), \
         patch("agent.main.SyncSession") as mock_session_cls, \
         patch("agent.main.guardar_mensaje", AsyncMock()) as mock_guardar, \
         patch("agent.main.enviar_mensaje_seguro", AsyncMock()) as mock_enviar, \
         patch("asyncio.sleep", AsyncMock(side_effect=[None, ValueError("stop")])):
        
        mock_session = mock_session_cls.return_value.__enter__.return_value
        mock_session.query.return_value.filter.return_value.first.return_value = mock_contacto
        
        try:
            await _revisar_inactividad()
        except ValueError:
            pass
            
        mock_guardar.assert_called_once_with("12345", "assistant", MENSAJE_CHECKIN_1, conversacion_id=42)
        mock_enviar.assert_called_once_with("12345", MENSAJE_CHECKIN_1, canal="telegram")


@pytest.mark.asyncio
async def test_revisar_inactividad_ultimo_mensaje_asistente_normal():
    """_revisar_inactividad sends CHECKIN_1 if last message is a normal assistant response and timeout passed."""
    from agent.main import _revisar_inactividad, MENSAJE_CHECKIN_1
    
    mock_contacto = MagicMock()
    mock_contacto.canal = "meta"
    
    with patch("agent.main.telefonos_con_actividad_reciente", AsyncMock(return_value=["12345"])), \
         patch("agent.main.ultimo_mensaje", AsyncMock(return_value={"role": "assistant", "content": "Aquí tienes los precios.", "timestamp": datetime.now(timezone.utc) - timedelta(seconds=1000)})), \
         patch("agent.main.obtener_conversacion_activa", AsyncMock(return_value=42)), \
         patch("agent.main.SyncSession") as mock_session_cls, \
         patch("agent.main.guardar_mensaje", AsyncMock()) as mock_guardar, \
         patch("agent.main.enviar_mensaje_seguro", AsyncMock()) as mock_enviar, \
         patch("asyncio.sleep", AsyncMock(side_effect=[None, ValueError("stop")])):
        
        mock_session = mock_session_cls.return_value.__enter__.return_value
        mock_session.query.return_value.filter.return_value.first.return_value = mock_contacto
        
        try:
            await _revisar_inactividad()
        except ValueError:
            pass
            
        mock_guardar.assert_called_once_with("12345", "assistant", MENSAJE_CHECKIN_1, conversacion_id=42)
        mock_enviar.assert_called_once_with("12345", MENSAJE_CHECKIN_1, canal="meta")


@pytest.mark.asyncio
async def test_revisar_inactividad_transicion_checkin2():
    """_revisar_inactividad sends CHECKIN_2 if last message was CHECKIN_1."""
    from agent.main import _revisar_inactividad, MENSAJE_CHECKIN_1, MENSAJE_CHECKIN_2
    
    mock_contacto = MagicMock()
    mock_contacto.canal = "meta"
    
    with patch("agent.main.telefonos_con_actividad_reciente", AsyncMock(return_value=["12345"])), \
         patch("agent.main.ultimo_mensaje", AsyncMock(return_value={"role": "assistant", "content": MENSAJE_CHECKIN_1, "timestamp": datetime.now(timezone.utc) - timedelta(seconds=1000)})), \
         patch("agent.main.obtener_conversacion_activa", AsyncMock(return_value=42)), \
         patch("agent.main.SyncSession") as mock_session_cls, \
         patch("agent.main.guardar_mensaje", AsyncMock()) as mock_guardar, \
         patch("agent.main.enviar_mensaje_seguro", AsyncMock()) as mock_enviar, \
         patch("asyncio.sleep", AsyncMock(side_effect=[None, ValueError("stop")])):
        
        mock_session = mock_session_cls.return_value.__enter__.return_value
        mock_session.query.return_value.filter.return_value.first.return_value = mock_contacto
        
        try:
            await _revisar_inactividad()
        except ValueError:
            pass
            
        mock_guardar.assert_called_once_with("12345", "assistant", MENSAJE_CHECKIN_2, conversacion_id=42)
        mock_enviar.assert_called_once_with("12345", MENSAJE_CHECKIN_2, canal="meta")


@pytest.mark.asyncio
async def test_revisar_inactividad_cierre_completo():
    """_revisar_inactividad sends CIERRE, clears history and finalizes if last message was CHECKIN_2."""
    from agent.main import _revisar_inactividad, MENSAJE_CHECKIN_2, MENSAJE_CIERRE
    
    mock_contacto = MagicMock()
    mock_contacto.canal = "meta"
    
    with patch("agent.main.telefonos_con_actividad_reciente", AsyncMock(return_value=["12345"])), \
         patch("agent.main.ultimo_mensaje", AsyncMock(return_value={"role": "assistant", "content": MENSAJE_CHECKIN_2, "timestamp": datetime.now(timezone.utc) - timedelta(seconds=1000)})), \
         patch("agent.main.obtener_conversacion_activa", AsyncMock(return_value=42)), \
         patch("agent.main.SyncSession") as mock_session_cls, \
         patch("agent.main.guardar_mensaje", AsyncMock()) as mock_guardar, \
         patch("agent.main.enviar_mensaje_seguro", AsyncMock()) as mock_enviar, \
         patch("agent.main.limpiar_historial", AsyncMock()) as mock_limpiar, \
         patch("agent.tools.finalizar_conversacion") as mock_finalizar, \
         patch("asyncio.sleep", AsyncMock(side_effect=[None, ValueError("stop")])):
        
        mock_session = mock_session_cls.return_value.__enter__.return_value
        mock_session.query.return_value.filter.return_value.first.return_value = mock_contacto
        
        try:
            await _revisar_inactividad()
        except ValueError:
            pass
            
        mock_guardar.assert_called_once_with("12345", "assistant", MENSAJE_CIERRE, conversacion_id=42)
        mock_enviar.assert_called_once_with("12345", MENSAJE_CIERRE, canal="meta")
        mock_limpiar.assert_called_once_with("12345")
        mock_finalizar.assert_called_once_with("12345", "inactividad")

