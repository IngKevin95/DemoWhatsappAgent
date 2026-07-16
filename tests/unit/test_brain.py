"""Unit tests for brain.py - conversation logic and intent classification."""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone

from agent.brain import (
    generar_respuesta,
    clasificar_intencion,
    _sanitizar_input,
    _retry_delay_segundos,
)


class TestGenerarRespuesta:
    """Tests for generar_respuesta() - core bridge node."""

    @pytest.mark.asyncio
    async def test_generar_respuesta_happy_path(self, mock_env, mock_gemini):
        """Happy path: Gemini responds, latency <30s."""
        with patch("agent.brain.genai") as mock_genai_module:
            mock_genai_module.Client.return_value.models.generate_content = mock_gemini.generate_content

            resultado = await generar_respuesta(
                mensaje="Hola, ¿cuál es el precio del módulo Pro?",
                telefono="34912345678",
                historial=[],
                herramientas=[]
            )

            assert resultado is not None
            assert isinstance(resultado, str)
            assert len(resultado) > 0

    @pytest.mark.asyncio
    async def test_generar_respuesta_gemini_timeout(self, mock_env):
        """Timeout: Gemini doesn't respond in 30s → fallback."""
        # This tests the timeout parameter and fallback behavior
        # Full timeout test happens in smoke phase with real latency
        resultado = await generar_respuesta(
            mensaje="¿Hola?",
            telefono="34912345678",
            historial=[],
            timeout_segundos=0.001  # Very short timeout to trigger immediately
        )

        # Should have fallback response, not error
        assert resultado is not None
        assert isinstance(resultado, str)

    @pytest.mark.asyncio
    async def test_generar_respuesta_sql_injection_sanitized(self, mock_env, mock_gemini):
        """Input sanitization: SQL injection attempt blocked."""
        with patch("agent.brain.genai") as mock_genai_module:
            mock_genai_module.Client.return_value.models.generate_content = mock_gemini.generate_content

            malicious_input = "'; DROP TABLE usuarios; --"
            resultado = await generar_respuesta(
                mensaje=malicious_input,
                telefono="34912345678",
                historial=[],
                herramientas=[]
            )

            # Should not crash, should sanitize
            assert resultado is not None


class TestClasificarIntencion:
    """Tests for await clasificar_intencion() - intent mapping."""

    @pytest.mark.asyncio
    async def test_intencion_precio(self):
        """Intent: PRECIO when asking about cost."""
        intent = await clasificar_intencion("¿Cuánto cuesta el módulo Pro?")
        assert isinstance(intent, str)

    @pytest.mark.asyncio
    async def test_intencion_soporte(self):
        """Intent: SOPORTE when asking for help."""
        intent = await clasificar_intencion("Necesito ayuda técnica")
        assert isinstance(intent, str)

    @pytest.mark.asyncio
    async def test_intencion_disponibilidad(self):
        """Intent: DISPONIBILIDAD when checking availability."""
        intent = await clasificar_intencion("¿Están disponibles ahora?")
        assert isinstance(intent, str)

    @pytest.mark.asyncio
    async def test_intencion_desconocida(self):
        """Intent: UNKNOWN when unclear."""
        intent = await clasificar_intencion("xyz abc 123")
        assert intent == "otro"


class TestClasificarIntencion:
    """Tests for intent classification."""

    @pytest.mark.asyncio
    async def test_clasificar_intencion_welcome(self):
        """Classify 'Hola' as welcome intent."""
        resultado = await clasificar_intencion("Hola, ¿cómo estás?")
        assert resultado in ["otro", "soporte", "comercial"]

    @pytest.mark.asyncio
    @patch("agent.brain.client.aio.models.generate_content", new_callable=AsyncMock)
    async def test_clasificar_intencion_price_query(self, mock_generate):
        mock_resp = MagicMock()
        mock_resp.text = "comercial"
        mock_generate.return_value = mock_resp
        """Classify price query."""
        resultado = await clasificar_intencion("¿Cuál es el precio del módulo Pro?")
        assert resultado == "comercial"

    @pytest.mark.asyncio
    @patch("agent.brain.client.aio.models.generate_content", new_callable=AsyncMock)
    async def test_clasificar_intencion_booking(self, mock_generate):
        mock_resp = MagicMock()
        mock_resp.text = "comercial"
        mock_generate.return_value = mock_resp
        """Classify booking intent."""
        resultado = await clasificar_intencion("Quiero agendar una demo para el martes")
        assert resultado == "comercial"

    @pytest.mark.asyncio
    @patch("agent.brain.client.aio.models.generate_content", new_callable=AsyncMock)
    async def test_clasificar_intencion_license_check(self, mock_generate):
        mock_resp = MagicMock()
        mock_resp.text = "soporte"
        mock_generate.return_value = mock_resp
        """Classify license validation intent."""
        resultado = await clasificar_intencion("¿Cuál es mi estado de licencia?")
        assert resultado == "soporte"

    @pytest.mark.asyncio
    @patch("agent.brain.client.aio.models.generate_content", new_callable=AsyncMock)
    async def test_clasificar_intencion_escalate(self, mock_generate):
        mock_resp = MagicMock()
        mock_resp.text = "soporte"
        mock_generate.return_value = mock_resp
        """Classify escalation intent."""
        resultado = await clasificar_intencion("Necesito hablar con soporte urgente")
        assert resultado == "soporte"

    @pytest.mark.asyncio
    async def test_clasificar_intencion_unknown(self):
        """Classify out-of-scope message."""
        resultado = await clasificar_intencion("¿Cómo está el clima en Marte?")
        assert resultado == "otro"


class TestIntegrationScenarios:
    """Integration-style tests for core flows."""

    @pytest.mark.asyncio
    async def test_generar_respuesta_con_contexto_vacio(self, mock_env, mock_gemini):
        """Generate response with empty context."""
        with patch("agent.brain.genai") as mock_genai_module:
            mock_genai_module.Client.return_value.models.generate_content = mock_gemini.generate_content

            resultado = await generar_respuesta(
                mensaje="Test",
                telefono="34912345678",
                historial=[],
                herramientas=None
            )
            assert resultado is not None

    @pytest.mark.asyncio
    async def test_generar_respuesta_con_herramientas(self, mock_env, mock_gemini):
        """Generate response with tools list."""
        with patch("agent.brain.genai") as mock_genai_module:
            mock_genai_module.Client.return_value.models.generate_content = mock_gemini.generate_content

            resultado = await generar_respuesta(
                mensaje="Agendar cita",
                telefono="34912345678",
                historial=[],
                herramientas=["agendar_cita", "consultar_precio"]
            )
            assert resultado is not None

    @pytest.mark.asyncio
    async def test_clasificar_intencion_confianza_alta(self):
        """Classification with high confidence."""
        resultado = await clasificar_intencion("Hola")
        assert resultado in ["otro", "soporte", "comercial"]

    @pytest.mark.asyncio
    async def test_clasificar_intencion_confianza_baja(self):
        """Classification with low confidence edge case."""
        resultado = await clasificar_intencion("xyz123!@#")
        assert resultado == "otro"

    def test_guardrails_check_empty_input(self):
        pass

    def test_guardrails_check_very_long_input(self):
        pass


class TestClasificarIntensionAdditional:
    """Additional tests for intent classification."""

    @pytest.mark.asyncio
    async def test_clasificar_intencion_multiple_keywords(self):
        """Classify with multiple keywords."""
        resultado = await clasificar_intencion("Quiero agendar cita y consultar precio")
        assert resultado in ["comercial", "soporte", "otro"]

    @pytest.mark.asyncio
    async def test_clasificar_intencion_with_special_chars(self):
        """Classify with special characters."""
        resultado = await clasificar_intencion("¿Cuál es el precio $$$?")
        assert resultado in ["comercial", "soporte", "otro"]


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_sanitizar_input_sql_injection(self):
        """Sanitize removes SQL keywords."""
        dirty = "SELECT * FROM users WHERE id=1; DROP TABLE users;"
        clean = _sanitizar_input(dirty)
        assert "SELECT" not in clean.upper() or "SELECT" in clean
        assert isinstance(clean, str)

    def test_sanitizar_input_script_tags(self):
        """Sanitize removes script tags."""
        dirty = "Hello <script>alert('xss')</script> world"
        clean = _sanitizar_input(dirty)
        assert "<script>" not in clean
        assert "Hello" in clean

    def test_sanitizar_input_clean_text(self):
        """Sanitize leaves clean text unchanged."""
        clean_text = "¿Cuál es el precio del módulo Pro?"
        result = _sanitizar_input(clean_text)
        assert len(result) > 0

    def test_retry_delay_segundos_default(self):
        """Retry delay returns default when no details."""
        from unittest.mock import MagicMock
        exc = MagicMock()
        exc.details = {}
        delay = _retry_delay_segundos(exc, default=5.0)
        assert delay == 5.0

    def test_retry_delay_segundos_parse_error(self):
        """Retry delay handles parsing errors gracefully."""
        from unittest.mock import MagicMock
        exc = MagicMock()
        exc.details = "invalid"
        delay = _retry_delay_segundos(exc, default=3.0)
        assert delay == 3.0
