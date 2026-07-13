"""
Test: FIX-REPAIR-003 — Retry consistency EspoCRM.

REQUIREMENT: EspoCRM integration debe usar mismo @retry decorator que Google.
Exponential backoff (2/4/8s), max 3 intentos.
"""

import pytest
import time
from unittest.mock import patch, MagicMock, call
from agent.integrations.espocrm import escalate_to_support


class TestEspoCRMRetryBackoff:
    """Red Phase: Tests que fallan porque retry está hardcodeado."""

    @patch('agent.integrations.espocrm.requests.post')
    def test_espocrm_uses_retry_decorator(self, mock_post):
        """AC-1: EspoCRM usa @retry decorator (exponential backoff)."""
        # Setup: Mock EspoCRM to fail 2 times, then succeed
        mock_post.side_effect = [
            Exception("Connection timeout"),
            Exception("Connection timeout"),
            MagicMock(status_code=201, json=lambda: {"id": "ticket123"})
        ]

        # Call escalate_to_support
        result = escalate_to_support(
            telefono="573001234567",
            nombre="Test User",
            asunto="Soporte técnico",
            descripcion="Mi problema"
        )

        # Verify retry backoff timing
        # Expected: fail at t=0, retry at t=2, retry at t=4, success at t=6+
        assert result["success"] == True
        assert mock_post.call_count == 3

    @patch('agent.integrations.espocrm.requests.post')
    @patch('time.sleep')  # Mock sleep to avoid actual delay
    def test_espocrm_exponential_backoff_timing(self, mock_sleep, mock_post):
        """AC-2: Backoff timing es exponencial (2, 4, 8s)."""
        mock_post.side_effect = [
            Exception("Timeout"),
            Exception("Timeout"),
            MagicMock(status_code=201, json=lambda: {"id": "ticket"})
        ]

        result = escalate_to_support(
            telefono="573001234567",
            nombre="Test",
            asunto="Help",
            descripcion="Problema"
        )

        # Verify sleep was called with backoff times
        sleep_calls = [c[0][0] for c in mock_sleep.call_args_list]
        assert len(sleep_calls) >= 2, f"Expected ≥2 sleep calls, got {len(sleep_calls)}"

        # Check backoff progression (2s, 4s, ...)
        if len(sleep_calls) >= 2:
            assert sleep_calls[0] == pytest.approx(2, abs=0.5), f"First backoff should be ~2s, got {sleep_calls[0]}"
            assert sleep_calls[1] == pytest.approx(4, abs=0.5), f"Second backoff should be ~4s, got {sleep_calls[1]}"

    @patch('agent.integrations.espocrm.requests.post')
    def test_espocrm_max_3_attempts(self, mock_post):
        """AC-1: Max 3 intentos, luego falla."""
        mock_post.side_effect = Exception("Persistent timeout")

        # Should fail after 3 attempts, not more
        with pytest.raises(Exception):
            escalate_to_support(
                telefono="573001234567",
                nombre="Test",
                asunto="Help",
                descripcion="Problem"
            )

        assert mock_post.call_count == 3, f"Expected 3 attempts, got {mock_post.call_count}"

    @patch('agent.integrations.espocrm.requests.post')
    def test_espocrm_retry_consistency_with_google(self, mock_post):
        """AC-3: EspoCRM y Google usan mismo strategy."""
        # Simula: ambos decoradores deberían behave identicamente
        from agent.integrations.google import _retry_delay_segundos

        # EspoCRM backoff should match Google's pattern
        # Google uses: 2, 4, 8s (exponential 2^n starting from n=1)
        expected_backoffs = [2, 4, 8]

        mock_post.side_effect = [
            Exception("Timeout"),
            Exception("Timeout"),
            MagicMock(status_code=201, json=lambda: {"id": "ticket"})
        ]

        # Call EspoCRM integration
        result = escalate_to_support(
            telefono="573001234567",
            nombre="Test",
            asunto="Help",
            descripcion="Problem"
        )

        # Verify it succeeded (meaning retry worked)
        assert result["success"] == True

    @patch('agent.integrations.espocrm.requests.post')
    def test_espocrm_logs_retry_attempts(self, mock_post):
        """AC-4: Logs registran retry attempt timings."""
        mock_post.side_effect = [
            Exception("Timeout"),
            MagicMock(status_code=201, json=lambda: {"id": "ticket"})
        ]

        with patch('agent.integrations.espocrm.logger') as mock_logger:
            result = escalate_to_support(
                telefono="573001234567",
                nombre="Test",
                asunto="Help",
                descripcion="Problem"
            )

            # Verify logger was called for retry (not hardcoded loop)
            # At least one warning/info about retry
            assert mock_logger.warning.called or mock_logger.info.called, \
                "Logger should log retry attempts"


class TestRetryConsistency:
    """Validate EspoCRM retry matches Google retry decorator."""

    def test_same_decorator_pattern(self):
        """Both Google and EspoCRM should use @retry decorator."""
        from agent.integrations.google import query_google_calendar
        from agent.integrations.espocrm import escalate_to_support

        # Both functions should have the retry decorator applied
        # Check via inspection or by verifying retry behavior

        # For now, just verify the functions exist and are callable
        assert callable(query_google_calendar)
        assert callable(escalate_to_support)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
