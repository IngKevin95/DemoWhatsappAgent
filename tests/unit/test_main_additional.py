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


def _make_async_session_mock(conv=None, msg=None, contacto=None):
    """Helper: returns a mock async context manager for SessionLocal."""
    mock_session = AsyncMock()

    # conv result
    conv_scalars = MagicMock()
    conv_scalars.first.return_value = conv
    conv_execute_result = MagicMock()
    conv_execute_result.scalars.return_value = conv_scalars

    # msg result
    msg_scalars = MagicMock()
    msg_scalars.first.return_value = msg
    msg_execute_result = MagicMock()
    msg_execute_result.scalars.return_value = msg_scalars

    # cierre_msg result (select Mensaje for delete in cierre path)
    del_scalars = MagicMock()
    del_scalars.all.return_value = []
    del_execute_result = MagicMock()
    del_execute_result.scalars.return_value = del_scalars

    # execute side_effect: first call = conv, second = msg, subsequent = del
    mock_session.execute = AsyncMock(side_effect=[
        conv_execute_result,
        msg_execute_result,
        del_execute_result,
    ])
    mock_session.get = AsyncMock(return_value=contacto)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.delete = AsyncMock()

    # async context manager protocol
    async_cm = AsyncMock()
    async_cm.__aenter__ = AsyncMock(return_value=mock_session)
    async_cm.__aexit__ = AsyncMock(return_value=False)

    return async_cm, mock_session


@pytest.mark.asyncio
async def test_revisar_inactividad_sin_conversacion_activa():
    """_revisar_inactividad should do nothing if no open conversation."""
    from agent.main import _revisar_inactividad

    async_cm, mock_session = _make_async_session_mock(conv=None)

    with patch("agent.main.telefonos_con_actividad_reciente", AsyncMock(return_value=["12345"])), \
         patch("agent.main.SessionLocal", return_value=async_cm), \
         patch("agent.main.enviar_mensaje_seguro", AsyncMock()) as mock_enviar, \
         patch("asyncio.sleep", AsyncMock(side_effect=[None, ValueError("stop")])):

        try:
            await _revisar_inactividad()
        except ValueError:
            pass

        mock_session.add.assert_not_called()
        mock_enviar.assert_not_called()


@pytest.mark.asyncio
async def test_revisar_inactividad_ultimo_mensaje_usuario():
    """_revisar_inactividad sends CHECKIN_1 if last message is from user and timeout passed."""
    from agent.main import _revisar_inactividad, MENSAJE_CHECKIN_1
    from agent.memory import Mensaje

    mock_conv = MagicMock()
    mock_conv.id = 42

    mock_msg = MagicMock(spec=Mensaje)
    mock_msg.role = "user"
    mock_msg.content = "hola"
    mock_msg.timestamp = datetime.now(timezone.utc) - timedelta(seconds=1000)

    mock_contacto = MagicMock()
    mock_contacto.canal = "telegram"

    async_cm, mock_session = _make_async_session_mock(conv=mock_conv, msg=mock_msg, contacto=mock_contacto)

    with patch("agent.main.telefonos_con_actividad_reciente", AsyncMock(return_value=["12345"])), \
         patch("agent.main.SessionLocal", return_value=async_cm), \
         patch("agent.main.enviar_mensaje_seguro", AsyncMock()) as mock_enviar, \
         patch("asyncio.sleep", AsyncMock(side_effect=[None, ValueError("stop")])):

        try:
            await _revisar_inactividad()
        except ValueError:
            pass

        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert added.content == MENSAJE_CHECKIN_1
        assert added.role == "assistant"
        mock_session.commit.assert_called_once()
        mock_enviar.assert_called_once_with("12345", MENSAJE_CHECKIN_1, canal="telegram")


@pytest.mark.asyncio
async def test_revisar_inactividad_ultimo_mensaje_asistente_normal():
    """_revisar_inactividad sends CHECKIN_1 if last message is a normal assistant response and timeout passed."""
    from agent.main import _revisar_inactividad, MENSAJE_CHECKIN_1
    from agent.memory import Mensaje

    mock_conv = MagicMock()
    mock_conv.id = 42

    mock_msg = MagicMock(spec=Mensaje)
    mock_msg.role = "assistant"
    mock_msg.content = "Aquí tienes los precios."
    mock_msg.timestamp = datetime.now(timezone.utc) - timedelta(seconds=1000)

    mock_contacto = MagicMock()
    mock_contacto.canal = "meta"

    async_cm, mock_session = _make_async_session_mock(conv=mock_conv, msg=mock_msg, contacto=mock_contacto)

    with patch("agent.main.telefonos_con_actividad_reciente", AsyncMock(return_value=["12345"])), \
         patch("agent.main.SessionLocal", return_value=async_cm), \
         patch("agent.main.enviar_mensaje_seguro", AsyncMock()) as mock_enviar, \
         patch("asyncio.sleep", AsyncMock(side_effect=[None, ValueError("stop")])):

        try:
            await _revisar_inactividad()
        except ValueError:
            pass

        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert added.content == MENSAJE_CHECKIN_1
        mock_session.commit.assert_called_once()
        mock_enviar.assert_called_once_with("12345", MENSAJE_CHECKIN_1, canal="meta")


@pytest.mark.asyncio
async def test_revisar_inactividad_transicion_checkin2():
    """_revisar_inactividad sends CHECKIN_2 if last message was CHECKIN_1."""
    from agent.main import _revisar_inactividad, MENSAJE_CHECKIN_1, MENSAJE_CHECKIN_2
    from agent.memory import Mensaje

    mock_conv = MagicMock()
    mock_conv.id = 42

    mock_msg = MagicMock(spec=Mensaje)
    mock_msg.role = "assistant"
    mock_msg.content = MENSAJE_CHECKIN_1
    mock_msg.timestamp = datetime.now(timezone.utc) - timedelta(seconds=1000)

    mock_contacto = MagicMock()
    mock_contacto.canal = "meta"

    async_cm, mock_session = _make_async_session_mock(conv=mock_conv, msg=mock_msg, contacto=mock_contacto)

    with patch("agent.main.telefonos_con_actividad_reciente", AsyncMock(return_value=["12345"])), \
         patch("agent.main.SessionLocal", return_value=async_cm), \
         patch("agent.main.enviar_mensaje_seguro", AsyncMock()) as mock_enviar, \
         patch("asyncio.sleep", AsyncMock(side_effect=[None, ValueError("stop")])):

        try:
            await _revisar_inactividad()
        except ValueError:
            pass

        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert added.content == MENSAJE_CHECKIN_2
        mock_session.commit.assert_called_once()
        mock_enviar.assert_called_once_with("12345", MENSAJE_CHECKIN_2, canal="meta")


@pytest.mark.asyncio
async def test_revisar_inactividad_cierre_completo():
    """_revisar_inactividad sends CIERRE, closes conversation and clears history."""
    from agent.main import _revisar_inactividad, MENSAJE_CHECKIN_2, MENSAJE_CIERRE
    from agent.memory import Mensaje

    mock_conv = MagicMock()
    mock_conv.id = 42
    mock_conv.estado = "abierta"
    mock_conv.espera_desde = None
    mock_conv.espera_hasta = None

    mock_msg = MagicMock(spec=Mensaje)
    mock_msg.role = "assistant"
    mock_msg.content = MENSAJE_CHECKIN_2
    mock_msg.timestamp = datetime.now(timezone.utc) - timedelta(seconds=1000)

    mock_contacto = MagicMock()
    mock_contacto.canal = "meta"

    async_cm, mock_session = _make_async_session_mock(conv=mock_conv, msg=mock_msg, contacto=mock_contacto)

    with patch("agent.main.telefonos_con_actividad_reciente", AsyncMock(return_value=["12345"])), \
         patch("agent.main.SessionLocal", return_value=async_cm), \
         patch("agent.main.enviar_mensaje_seguro", AsyncMock()) as mock_enviar, \
         patch("asyncio.sleep", AsyncMock(side_effect=[None, ValueError("stop")])):

        try:
            await _revisar_inactividad()
        except ValueError:
            pass

        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert added.content == MENSAJE_CIERRE
        mock_session.commit.assert_called_once()
        assert mock_conv.estado == "cerrada"
        assert mock_conv.motivo_cierre == "inactividad"
        mock_enviar.assert_called_once_with("12345", MENSAJE_CIERRE, canal="meta")
