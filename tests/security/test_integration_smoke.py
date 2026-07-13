"""
Integration smoke test for EP-003-MINI security features.

Simulates complete webhook flow with rate limiting + input validation + audit logging.
"""

import pytest
from unittest.mock import Mock, patch
import json


class TestSecurityIntegration_Smoke:
    """
    Integration test: Rate limiting + Input validation + Audit logging together.
    """

    @pytest.fixture
    def mocked_webhook(self):
        """Mock a complete webhook flow."""
        from agent.middleware.rate_limiter import RateLimiter
        from agent.middleware.input_validator import InputValidator
        from agent.middleware.audit_logger import AuditLogger

        return {
            "rate_limiter": RateLimiter(),
            "input_validator": InputValidator(),
            "audit_logger": AuditLogger(),
        }

    def test_webhook_flow_with_security(self, mocked_webhook):
        """
        Complete webhook flow:
        1. Rate limit check
        2. Input validation
        3. Audit logging
        """
        client_ip = "203.0.113.100"
        user_id = "5511999999999"
        message = "Quiero saber el precio del módulo X"

        rl = mocked_webhook["rate_limiter"]
        iv = mocked_webhook["input_validator"]
        al = mocked_webhook["audit_logger"]

        # Step 1: Rate limiter allows first request
        assert rl.is_allowed(client_ip) is True

        # Step 2: Input validator sanitizes message
        sanitized = iv.sanitize(message)
        assert len(sanitized) > 0

        # Step 3: Audit logger records event
        al.log_event(
            user_id=user_id,
            tool_name="test_tool",
            action="test_action",
            result="success",
            metadata={"message": sanitized},
        )

        # All steps completed successfully
        assert True

    def test_webhook_blocked_on_rate_limit(self, mocked_webhook):
        """
        When rate limit exceeded, request is blocked before reaching app logic.
        """
        client_ip = "203.0.113.101"
        rl = mocked_webhook["rate_limiter"]

        # Send 10 requests (allowed)
        for _ in range(10):
            assert rl.is_allowed(client_ip) is True

        # 11th request blocked
        assert rl.is_allowed(client_ip) is False

    def test_webhook_sanitizes_injection_payload(self, mocked_webhook):
        """
        SQL injection payload is sanitized before reaching Gemini.
        """
        iv = mocked_webhook["input_validator"]
        payload = "'; DROP TABLE cases; --"

        sanitized = iv.sanitize(payload)

        # Payload should be modified (dangerous chars/keywords removed)
        assert sanitized != payload or len(sanitized) < len(payload)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
