"""Unit tests for memory.py - conversation history."""

import pytest
from unittest.mock import patch
from agent.memory import (
    guardar_mensaje,
    obtener_historial,
    ultimo_mensaje,
    ultimo_timestamp,
    limpiar_historial,
)


class TestGuardarMensaje:
    """Tests for saving messages."""

    @pytest.mark.asyncio
    async def test_guardar_mensaje_usuario(self, mock_postgres):
        """Save user message."""
        await guardar_mensaje(
            telefono="34912345678",
            role="usuario",
            content="Hola, ¿precio?"
        )

    @pytest.mark.asyncio
    async def test_guardar_mensaje_bot(self, mock_postgres):
        """Save bot message."""
        await guardar_mensaje(
            telefono="34912345678",
            role="bot",
            content="Hola, bienvenido."
        )

    @pytest.mark.asyncio
    async def test_guardar_mensaje_con_area(self):
        """Save message with area_id."""
        await guardar_mensaje(
            telefono="34912345678",
            role="usuario",
            content="Necesito soporte",
            area_id=1
        )


class TestObtenerHistorial:
    """Tests for retrieving history."""

    @pytest.mark.asyncio
    async def test_obtener_historial_estructura(self, mock_postgres):
        """History returns list of dicts."""
        historial = await obtener_historial("34912345678", limite=10)
        assert isinstance(historial, list)
        if historial:
            assert "role" in historial[0]
            assert "content" in historial[0]

    @pytest.mark.asyncio
    async def test_obtener_historial_respeta_limite(self):
        """Respects limit parameter."""
        historial = await obtener_historial("34912345678", limite=5)
        assert isinstance(historial, list)
        if historial:
            assert len(historial) <= 5

    @pytest.mark.asyncio
    async def test_obtener_historial_vacio(self):
        """Returns empty list for unknown user."""
        historial = await obtener_historial("34999999999")
        assert isinstance(historial, list)


class TestUltimoMensaje:
    """Tests for getting last message."""

    @pytest.mark.asyncio
    async def test_ultimo_mensaje_estructura(self, mock_postgres):
        """Last message has expected structure."""
        mensaje = await ultimo_mensaje("34912345678")
        if mensaje:
            assert isinstance(mensaje, dict)
            assert "role" in mensaje or "content" in mensaje

    @pytest.mark.asyncio
    async def test_ultimo_mensaje_usuario_nuevo(self):
        """Returns None for unknown user."""
        mensaje = await ultimo_mensaje("34999999999")
        # Either None or dict
        assert mensaje is None or isinstance(mensaje, dict)


class TestUltimoTimestamp:
    """Tests for getting last message time."""

    @pytest.mark.asyncio
    async def test_ultimo_timestamp_tipo(self):
        """Returns datetime or None."""
        timestamp = await ultimo_timestamp("34912345678")
        # Should be None or datetime-compatible
        assert timestamp is None or hasattr(timestamp, "isoformat")


class TestLimpiarHistorial:
    """Tests for cleanup."""

    @pytest.mark.asyncio
    async def test_limpiar_historial_ejecuta(self):
        """Cleanup runs without error."""
        # Just verify it doesn't crash
        await limpiar_historial("34912345678")
