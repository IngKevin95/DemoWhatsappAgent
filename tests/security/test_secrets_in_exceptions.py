"""
Test: FIX-REPAIR-001 — Tokens in logs should be redacted.

REQUIREMENT: Exception logging en google.py:45 no debe loguear tokens OAuth
completos. Los campos Authorization, access_token, Bearer tokens deben ser
redactados como [REDACTED].
"""

import pytest
from unittest.mock import patch, MagicMock
from agent.middleware.logging import SanitizedLogger


class TestTokenSanitization:
    """Red Phase: Tests que fallan porque sanitization no existe aún."""

    def test_exception_logging_redacts_authorization_header(self):
        """AC-1: Authorization header redacted en exception logs."""
        logger = SanitizedLogger(__name__)

        # Simulate exception with Authorization header in response
        exception_text = (
            "Google API Error: 401 Unauthorized\n"
            "Response headers: Authorization: Bearer sk-proj-abc123xyz789\n"
            "Response body: {\"error\": \"invalid_token\"}"
        )

        # Mock a logger call and capture output
        with patch.object(logger, '_log') as mock_log:
            logger.exception(exception_text)

            # Verify that Authorization was redacted
            call_args = mock_log.call_args
            logged_message = str(call_args)

            assert "sk-proj-abc123xyz789" not in logged_message, \
                "Token should be redacted in logs"
            assert "[REDACTED]" in logged_message, \
                "Should show [REDACTED] placeholder"

    def test_exception_logging_redacts_access_token(self):
        """AC-2: access_token field redacted en exception logs."""
        logger = SanitizedLogger(__name__)

        exception_text = (
            "OAuth Error: access_token expired\n"
            "access_token: ya29.a0AfH6SMBx1234567890abcdefghijk\n"
            "expires_in: 3599"
        )

        with patch.object(logger, '_log') as mock_log:
            logger.exception(exception_text)

            call_args = str(mock_log.call_args)
            assert "ya29.a0AfH6SMBx1234567890abcdefghijk" not in call_args
            assert "[REDACTED]" in call_args

    def test_exception_logging_redacts_database_url(self):
        """AC-2: DATABASE_URL credential redacted."""
        logger = SanitizedLogger(__name__)

        exception_text = (
            "Database connection failed\n"
            "DATABASE_URL: postgresql://user:password123@localhost:5432/db\n"
            "Error: connection refused"
        )

        with patch.object(logger, '_log') as mock_log:
            logger.exception(exception_text)

            call_args = str(mock_log.call_args)
            assert "password123" not in call_args
            assert "localhost:5432" not in call_args

    def test_ci_security_gate_fails_if_tokens_in_logs(self):
        """AC-3: CI gate falla si encuentra token patterns en logs."""
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

        # Gate should fail if secrets found
        assert len(found_secrets) == 0, \
            f"CI gate should fail — found {len(found_secrets)} secret patterns"

    def test_sanitizer_preserves_safe_content(self):
        """AC-2: Sanitizer no toca contenido seguro."""
        logger = SanitizedLogger(__name__)

        safe_exception = (
            "ValueError: Invalid input format\n"
            "Function: validate_user_input\n"
            "Expected: string, got: int"
        )

        with patch.object(logger, '_log') as mock_log:
            logger.exception(safe_exception)

            call_args = str(mock_log.call_args)
            # Safe content should still appear
            assert "ValueError" in call_args
            assert "validate_user_input" in call_args


class TestGoogleIntegrationExceptionHandling:
    """Red Phase: Test google.py:45 exception logging."""

    @patch('agent.integrations.google.client.messages.create')
    def test_google_exception_redacts_oauth_token(self, mock_create):
        """AC-1: google.py:45 exception logging redacts tokens."""
        # Mock Google API to raise exception with token in response
        mock_response = MagicMock()
        mock_response.text = "Error: 401\nAuthorization: Bearer ya29.abc123def456"

        mock_create.side_effect = Exception("API Error")

        # This will fail until sanitized logging is implemented
        from agent.integrations.google import query_google_calendar

        # Capture logs
        with pytest.raises(Exception):
            query_google_calendar(user_email="test@example.com")

        # TODO: Assert that logs were sanitized
        # (requires log capture mechanism)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
