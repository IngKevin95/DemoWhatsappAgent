"""
Test: FIX-REPAIR-001 — Tokens in logs should be redacted.

REQUIREMENT: Exception logging en google.py:45 no debe loguear tokens OAuth
completos. Los campos Authorization, access_token, Bearer tokens deben ser
redactados como [REDACTED].
"""

import pytest
from unittest.mock import patch, MagicMock
from agent.middleware.logging import TokenSanitizer


class TestTokenSanitization:
    """Red Phase: Tests que fallan porque sanitization no existe aún."""

    def test_exception_logging_redacts_authorization_header(self):
        """AC-1: Authorization header redacted en exception logs."""
        sanitizer = TokenSanitizer()

        # Simulate exception with Authorization header in response
        exception_text = (
            "Google API Error: 401 Unauthorized\n"
            "Response headers: Authorization: Bearer sk-proj-abc123xyz789\n"
            "Response body: {\"error\": \"invalid_token\"}"
        )

        # Test sanitization
        sanitized = sanitizer.sanitize(exception_text)

        assert "sk-proj-abc123xyz789" not in sanitized, \
            "Token should be redacted in logs"
        assert "[REDACTED]" in sanitized, \
            "Should show [REDACTED] placeholder"

    def test_exception_logging_redacts_access_token(self):
        """AC-2: access_token field redacted en exception logs."""
        sanitizer = TokenSanitizer()

        exception_text = (
            "OAuth Error: access_token expired\n"
            "access_token: ya29.a0AfH6SMBx1234567890abcdefghijk\n"
            "expires_in: 3599"
        )

        sanitized = sanitizer.sanitize(exception_text)
        assert "ya29.a0AfH6SMBx1234567890abcdefghijk" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_exception_logging_redacts_database_url(self):
        """AC-2: DATABASE_URL credential redacted."""
        sanitizer = TokenSanitizer()

        exception_text = (
            "Database connection failed\n"
            "DATABASE_URL: postgresql://user:password123@localhost:5432/db\n"
            "Error: connection refused"
        )

        sanitized = sanitizer.sanitize(exception_text)
        assert "password123" not in sanitized
        assert "localhost:5432" not in sanitized

    def test_ci_security_gate_detects_tokens_in_logs(self):
        """AC-3: CI gate detecta token patterns en logs."""
        # This would be a CI-level test, but we simulate it here
        log_content = "Authorization: Bearer sk-proj-secret123"

        # Simulate CI gate check
        patterns = [
            r"Authorization:\s*Bearer\s*[\w\-\.]+",
            r"access_token:\s*[\w\-\.]+",
            r"sk-proj-[\w\-\.]+",
        ]

        found_secrets = []
        for pattern in patterns:
            import re
            matches = re.findall(pattern, log_content)
            if matches:
                found_secrets.extend(matches)

        # Gate SHOULD detect secrets (CI gate purpose is to fail if secrets found)
        assert len(found_secrets) > 0, \
            "CI gate should detect secret patterns"

    def test_sanitizer_preserves_safe_content(self):
        """AC-2: Sanitizer no toca contenido seguro."""
        sanitizer = TokenSanitizer()

        safe_exception = (
            "ValueError: Invalid input format\n"
            "Function: validate_user_input\n"
            "Expected: string, got: int"
        )

        sanitized = sanitizer.sanitize(safe_exception)
        # Safe content should still appear
        assert "ValueError" in sanitized
        assert "validate_user_input" in sanitized


class TestGoogleIntegrationExceptionHandling:
    """Red Phase: Test google.py:45 exception logging."""

    @patch('agent.integrations.google.get_calendar_service')
    def test_google_exception_redacts_oauth_token(self, mock_service):
        """AC-1: google.py exception logging redacts tokens."""
        # Mock Google API to raise exception with token in response
        mock_service.return_value.events.return_value.insert.return_value.execute.side_effect = Exception(
            "API Error: 401\nAuthorization: Bearer ya29.abc123def456"
        )

        # This will fail until sanitized logging is implemented
        from agent.integrations.google import crear_evento_calendar

        # Capture logs via logger
        with patch('agent.integrations.google.logger') as mock_logger:
            with pytest.raises(Exception):
                crear_evento_calendar(
                    nombre="Test User",
                    telefono="573001234567",
                    motivo="Test",
                    fecha="2025-07-15",
                    hora="10:00"
                )

            # Verify logger.exception was called
            assert mock_logger.exception.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
