"""
Tests for rate limiting middleware (HU-030).

AC-1: Rate Limit Enforced per IP
When IP sends 11 requests in 60 seconds, 11th request returns 429.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta


class TestRateLimitingHU030:
    """HU-030: Rate limiting on webhook."""

    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter instance."""
        from agent.middleware.rate_limiter import RateLimiter
        return RateLimiter(requests=10, window_seconds=60)

    def test_ac1_rate_limit_enforced_at_11th_request(self, rate_limiter):
        """
        AC-1: Rate Limit Enforced per IP

        Given IP has sent 10 requests in the last minute
        When it tries to send the 11th request
        Then webhook returns 429 with "Too many requests" message
        And request is NOT processed (doesn't reach Gemini or tools)
        And log records: source_ip, attempts_count, timestamp
        """
        test_ip = "203.0.113.10"

        # Send 10 requests (all should be allowed)
        for i in range(10):
            is_allowed = rate_limiter.is_allowed(test_ip)
            assert is_allowed is True, f"Request {i+1} should be allowed"

        # Send 11th request (should be blocked)
        is_allowed = rate_limiter.is_allowed(test_ip)
        assert is_allowed is False, "11th request should be rate limited"

    def test_ac2_rate_limit_reset_after_60_seconds(self, rate_limiter):
        """
        AC-2: Rate Limit Reset After 1 Minute

        Given IP was rate limited 61 seconds ago
        When it sends the next request
        Then counter resets to 0
        And request is processed normally (HTTP 200)
        And log records: reset_event, source_ip, timestamp
        """
        test_ip = "203.0.113.11"

        # Fill up the quota
        for _ in range(10):
            rate_limiter.is_allowed(test_ip)

        # 11th request should be blocked
        assert rate_limiter.is_allowed(test_ip) is False

        # Simulate 61 seconds passing by clearing old entries
        # (In real implementation, this would use timestamps)
        rate_limiter._reset_stale_entries(current_time=datetime.now() + timedelta(seconds=61))

        # Next request should be allowed (counter reset)
        is_allowed = rate_limiter.is_allowed(test_ip)
        assert is_allowed is True, "Request after reset should be allowed"

    def test_ac3_rate_limit_does_not_affect_different_ips(self, rate_limiter):
        """
        AC-3: Rate Limit NO Afecta IPs Diferentes

        Given IP-A sent 10 requests (limited)
        When IP-B sends a request
        Then IP-B is processed normally (not limited)
        And each IP has independent counter
        """
        ip_a = "203.0.113.20"
        ip_b = "203.0.113.21"

        # Fill up IP-A quota
        for _ in range(10):
            rate_limiter.is_allowed(ip_a)

        # IP-A is now limited
        assert rate_limiter.is_allowed(ip_a) is False

        # IP-B should NOT be limited (independent counter)
        assert rate_limiter.is_allowed(ip_b) is True

    def test_ac4_x_forwarded_for_header_handling(self, rate_limiter):
        """
        AC-4: Proxy/CDN IP Handling (Edge Case)

        Given client accesses via proxy (X-Forwarded-For: client_ip, proxy_ip, cdn_ip)
        When it sends requests
        Then rate limiter extracts client_ip correctly
        And counter is per client_ip, not proxy IP
        And log records: client_ip (extracted), proxy_chain, trusted_proxy_verified
        """
        client_ip = "203.0.113.30"
        proxy_chain = f"{client_ip}, 198.51.100.5, 192.0.2.1"

        # Extract client IP from X-Forwarded-For
        extracted_ip = rate_limiter.extract_client_ip(x_forwarded_for=proxy_chain)
        assert extracted_ip == client_ip, f"Should extract {client_ip} from chain"

        # Rate limiting should apply to client_ip, not proxy IPs
        for _ in range(10):
            rate_limiter.is_allowed(extracted_ip)

        # 11th should be blocked
        assert rate_limiter.is_allowed(extracted_ip) is False

    def test_logging_rate_limit_event(self, rate_limiter, caplog):
        """
        Verify rate limit event is logged in JSON format:
        {source_ip, requests_count, action="rate_limited", timestamp}
        """
        import logging
        test_ip = "203.0.113.40"

        # Send 11 requests
        with caplog.at_level(logging.DEBUG):  # Capture all levels
            for _ in range(11):
                rate_limiter.is_allowed(test_ip)

        # Check that rate limit event was logged
        # Log message should contain "rate limit" or "rate_limited"
        rate_limit_logs = [r for r in caplog.records if "rate limit" in r.getMessage().lower()]
        assert len(rate_limit_logs) > 0, f"Should log rate limit event. Logs: {[r.getMessage() for r in caplog.records]}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
