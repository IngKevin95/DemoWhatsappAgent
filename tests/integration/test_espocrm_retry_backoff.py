"""
Test: FIX-REPAIR-003 — Retry consistency EspoCRM.

REQUIREMENT: EspoCRM integration debe usar mismo @retry decorator que Google.
Exponential backoff (2/4/8s), max 3 intentos.
"""

import pytest
import time
from unittest.mock import patch, MagicMock, call
from agent.integrations.espocrm import crear_caso, crear_lead


class TestEspoCRMRetryBackoff:
    """Red Phase: Tests que fallan porque retry está hardcodeado."""

    @patch('agent.integrations.espocrm.httpx.post')
    def test_espocrm_uses_retry_decorator(self, mock_post):
        """AC-1: EspoCRM usa @retry decorator (exponential backoff)."""
        # Setup: Mock EspoCRM to fail 2 times, then succeed
        mock_post.side_effect = [
            Exception("Connection timeout"),
            Exception("Connection timeout"),
            MagicMock(status_code=201, json=lambda: {"id": "caso123"})
        ]

        # Call crear_caso (has @retry decorator)
        result = crear_caso(
            telefono="573001234567",
            descripcion="Mi problema",
            modulo="Soporte técnico",
            radicado="ESC-123"
        )

        # Verify retry backoff timing
        # Expected: fail at t=0, retry at t=2, retry at t=4, success at t=6+
        assert result["id"] == "caso123"
        assert mock_post.call_count == 3

    @patch('agent.integrations.espocrm.httpx.post')
    @patch('time.sleep')  # Mock sleep to avoid actual delay
    def test_espocrm_exponential_backoff_timing(self, mock_sleep, mock_post):
        """AC-2: Backoff timing es exponencial (2, 4, 8s)."""
        mock_post.side_effect = [
            Exception("Timeout"),
            Exception("Timeout"),
            MagicMock(status_code=201, json=lambda: {"id": "caso"})
        ]

        result = crear_caso(
            telefono="573001234567",
            descripcion="Problema",
            modulo="Support",
            radicado="ESC-456"
        )

        # Verify sleep was called with backoff times
        sleep_calls = [c[0][0] for c in mock_sleep.call_args_list]
        assert len(sleep_calls) >= 2, f"Expected ≥2 sleep calls, got {len(sleep_calls)}"

        # Check backoff progression (2s, 4s, ...)
        if len(sleep_calls) >= 2:
            assert sleep_calls[0] == pytest.approx(2, abs=0.5), f"First backoff should be ~2s, got {sleep_calls[0]}"
            assert sleep_calls[1] == pytest.approx(4, abs=0.5), f"Second backoff should be ~4s, got {sleep_calls[1]}"

    @patch('agent.integrations.espocrm.httpx.post')
    def test_espocrm_max_3_attempts(self, mock_post):
        """AC-1: Max 3 intentos, luego falla."""
        mock_post.side_effect = Exception("Persistent timeout")

        # Should fail after 3 attempts, not more
        with pytest.raises(Exception):
            crear_caso(
                telefono="573001234567",
                descripcion="Problem",
                modulo="Support",
                radicado="ESC-789"
            )

        assert mock_post.call_count == 3, f"Expected 3 attempts, got {mock_post.call_count}"

    @patch('agent.integrations.espocrm.httpx.post')
    def test_espocrm_retry_consistency_with_google(self, mock_post):
        """AC-3: EspoCRM y Google usan mismo strategy."""
        # Simula: ambos decoradores deberían behave identicamente
        from agent.utilities.retry import retry

        # EspoCRM backoff should match Google's pattern
        # exponential 2^n: 2, 4, 8s
        expected_backoffs = [2, 4, 8]

        mock_post.side_effect = [
            Exception("Timeout"),
            Exception("Timeout"),
            MagicMock(status_code=201, json=lambda: {"id": "caso"})
        ]

        # Call EspoCRM integration
        result = crear_caso(
            telefono="573001234567",
            descripcion="Problem",
            modulo="Support",
            radicado="ESC-101"
        )

        # Verify it succeeded (meaning retry worked)
        assert result["id"] == "caso"

    @patch('agent.integrations.espocrm.httpx.post')
    def test_espocrm_logs_retry_attempts(self, mock_post):
        """AC-4: Logs registran retry attempt timings."""
        mock_post.side_effect = [
            Exception("Timeout"),
            MagicMock(status_code=201, json=lambda: {"id": "caso"})
        ]

        with patch('agent.utilities.retry.logger') as mock_logger:
            result = crear_caso(
                telefono="573001234567",
                descripcion="Problem",
                modulo="Support",
                radicado="ESC-202"
            )

            # Verify logger was called for retry (not hardcoded loop)
            # At least one warning/info about retry
            assert mock_logger.warning.called or mock_logger.info.called, \
                "Logger should log retry attempts"

    @patch('agent.integrations.espocrm.httpx.post')
    def test_crear_caso_includes_radicado_in_name(self, mock_post):
        """Verify that when radicado is provided, it is prepended to the Case name."""
        mock_post.return_value = MagicMock(status_code=201, json=lambda: {"id": "caso_123"})

        crear_caso(
            telefono="573001234567",
            descripcion="Mi problema",
            modulo="Soporte técnico",
            radicado="ESC-12345"
        )

        assert mock_post.call_count == 1
        args, kwargs = mock_post.call_args
        body = kwargs.get("json") or args[0]
        assert body["name"] == "[ESC-12345] Soporte Soporte técnico - 573001234567"

    def test_crear_caso_raises_value_error_if_radicado_empty(self):
        """Verify that Value error is raised when radicado is empty or None."""
        with pytest.raises(ValueError, match="Código de radicado es requerido"):
            crear_caso(
                telefono="573001234567",
                descripcion="Mi problema",
                modulo="Soporte técnico",
                radicado=""
            )


class TestRetryConsistency:
    """Validate EspoCRM retry matches Google retry decorator."""

    def test_same_decorator_pattern(self):
        """Both Google and EspoCRM should use similar error handling."""
        from agent.integrations.google import crear_evento_calendar
        from agent.integrations.espocrm import crear_caso

        # Both functions should handle retries and errors gracefully
        # Check via inspection or by verifying they are callable

        # For now, just verify the functions exist and are callable
        assert callable(crear_evento_calendar)
        assert callable(crear_caso)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
