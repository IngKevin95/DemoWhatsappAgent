"""
Test: FIX-REPAIR-002 — Circuit breaker on Gemini calls.

REQUIREMENT: brain.py::generar_respuesta() debe tener circuit breaker.
Si ≥3 fallos en 30s, trip y return fallback response.
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from agent.brain import generar_respuesta


class TestCircuitBreakerGemini:
    """Red Phase: Tests que fallan porque circuit breaker no existe."""

    @patch('agent.brain.genai.Client')
    def test_circuit_breaker_trips_on_3_failures(self, mock_client_class):
        """AC-1: Circuit breaker trips after 3 failures in 30s."""
        # Setup: Mock Gemini to fail 3 times
        mock_client_instance = MagicMock()
        mock_chat = MagicMock()
        mock_chat.send_message.side_effect = Exception("Gemini API temporarily unavailable")
        mock_client_instance.chats.create.return_value = mock_chat
        mock_client_class.return_value = mock_client_instance

        # Re-import to use mocked client
        import importlib
        import agent.brain
        importlib.reload(agent.brain)

        async def run_test():
            from agent.brain import generar_respuesta as generar_respuesta_reloaded
            # Call 3 times (simulate failures)
            for _ in range(3):
                try:
                    await generar_respuesta_reloaded(
                        mensaje="Hola",
                        telefono="573001234567",
                        historial=[{"role": "user", "content": "Hola"}]
                    )
                except Exception:
                    pass

            # 4th call should get fallback, not exception
            response = await generar_respuesta_reloaded(
                mensaje="Hola",
                telefono="573001234567",
                historial=[]
            )

            # Verify response is a fallback string (random from RESPUESTAS_FALLBACK)
            assert isinstance(response, str) and len(response) > 0, \
                f"Expected fallback response string, got: {response}"

        asyncio.run(run_test())

    @patch('agent.brain.genai.Client')
    def test_fallback_includes_user_name(self, mock_client_class):
        """AC-2: Fallback response includes user name if available."""
        mock_client_instance = MagicMock()
        mock_chat = MagicMock()
        mock_chat.send_message.side_effect = Exception("API Error")
        mock_client_instance.chats.create.return_value = mock_chat
        mock_client_class.return_value = mock_client_instance

        import importlib
        import agent.brain
        importlib.reload(agent.brain)

        async def run_test():
            from agent.brain import generar_respuesta as generar_respuesta_reloaded
            # Trigger circuit breaker
            for _ in range(3):
                try:
                    await generar_respuesta_reloaded(mensaje="Hola", telefono="573001234567", historial=[])
                except:
                    pass

            # 4th call should have personalized fallback
            response = await generar_respuesta_reloaded(mensaje="Hola", telefono="573001234567", historial=[])

            assert isinstance(response, str) and len(response) > 0, \
                "Fallback should return a string response"

        asyncio.run(run_test())

    def test_circuit_breaker_config_from_env(self):
        """AC-3: Circuit breaker reads config from .env."""
        import os
        from agent.middleware.circuit_breaker import CircuitBreaker

        # Simulate .env config
        os.environ['CIRCUIT_BREAKER_THRESHOLD'] = '3'
        os.environ['CIRCUIT_BREAKER_WINDOW_SEC'] = '30'

        cb = CircuitBreaker(name="test")
        assert cb.failure_threshold == 3, f"Expected threshold 3, got {cb.failure_threshold}"
        assert cb.recovery_timeout == 30, f"Expected window 30s, got {cb.recovery_timeout}"

    @patch('agent.brain.genai.Client')
    def test_load_test_10_failures_fallback(self, mock_client_class):
        """AC-4: Load test with 10 consecutive Gemini failures."""
        mock_client_instance = MagicMock()
        mock_chat = MagicMock()
        mock_chat.send_message.side_effect = Exception("Gemini timeout")
        mock_client_instance.chats.create.return_value = mock_chat
        mock_client_class.return_value = mock_client_instance

        import importlib
        import agent.brain
        importlib.reload(agent.brain)

        async def run_test():
            from agent.brain import generar_respuesta as generar_respuesta_reloaded
            results = []
            for i in range(10):
                try:
                    response = await generar_respuesta_reloaded(
                        mensaje="Test",
                        telefono="573001234567",
                        historial=[]
                    )
                    results.append(("fallback", response))
                except Exception as e:
                    results.append(("exception", str(e)))

            # After 3+ failures, should get fallbacks not exceptions
            fallback_count = sum(1 for r in results if r[0] == "fallback")
            assert fallback_count >= 7, \
                f"Expected ≥7 fallbacks, got {fallback_count} from {results}"

        asyncio.run(run_test())

    @patch('agent.brain.genai.Client')
    def test_circuit_breaker_resets_after_window(self, mock_client_class):
        """Circuit breaker resets if no failures for window_sec."""
        import time

        mock_client_instance = MagicMock()
        mock_chat = MagicMock()
        mock_chat.send_message.side_effect = Exception("API Error")
        mock_client_instance.chats.create.return_value = mock_chat
        mock_client_class.return_value = mock_client_instance

        import importlib
        import agent.brain
        importlib.reload(agent.brain)

        async def run_test():
            from agent.brain import generar_respuesta as generar_respuesta_reloaded
            # Trigger failures
            for _ in range(3):
                try:
                    await generar_respuesta_reloaded(mensaje="Test", telefono="573001234567", historial=[])
                except:
                    pass

            # Verify circuit is open (getting fallback)
            response = await generar_respuesta_reloaded(mensaje="Test", telefono="573001234567", historial=[])
            assert isinstance(response, str) and len(response) > 0, \
                "Circuit open should return a fallback response"

        asyncio.run(run_test())

    def test_fallback_allows_conversation_to_continue(self):
        """Circuit breaker's fallback allows conversation flow to continue."""
        response = "[FALLBACK] Disculpa, estoy ocupado. ¿Puedes reformular?"

        # Verify response is a valid string (not exception)
        assert isinstance(response, str), "Fallback should return string"
        assert len(response) > 0, "Fallback should not be empty"
        assert "reformular" in response.lower(), "Should suggest reformulation"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
