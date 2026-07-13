"""
Test: HU-030 — Rate Limiting en Webhook

RED PHASE: Tests que esperan comportamiento de rate limiting.
"""

import pytest
from unittest.mock import patch, MagicMock
from agent.middleware.rate_limiter import RateLimiter
import time


class TestRateLimiterHU030:
    """HU-030 AC-1: Rate limit enforced por IP"""

    def test_rate_limit_blocks_after_10_requests_per_minute(self):
        """AC-1: Retorna 429 después de 10 requests por IP en 1 minuto."""
        limiter = RateLimiter(requests=10, window_seconds=60)

        # Simular 10 requests exitosos
        for i in range(10):
            is_allowed = limiter.is_allowed("192.168.1.100")
            assert is_allowed is True, f"Request {i+1} should be allowed"

        # 11° request debería ser bloqueado
        is_allowed = limiter.is_allowed("192.168.1.100")
        assert is_allowed is False, "11th request should be rate limited (429)"

    def test_rate_limit_reset_after_window_expires(self):
        """AC-2: Counter resetea después de que expire la ventana (60s)."""
        limiter = RateLimiter(requests=2, window_seconds=1)  # 1s window para test

        # Enviar 2 requests
        limiter.is_allowed("192.168.1.101")
        limiter.is_allowed("192.168.1.101")

        # 3° debería ser bloqueado
        assert limiter.is_allowed("192.168.1.101") is False

        # Esperar a que expire la ventana
        time.sleep(1.1)

        # Después de expiración, debería permitirse de nuevo
        assert limiter.is_allowed("192.168.1.101") is True

    def test_rate_limit_per_ip_isolation(self):
        """AC-3: Cada IP tiene contador independiente."""
        limiter = RateLimiter(requests=2, window_seconds=60)

        # IP-A: 2 requests (limitada)
        limiter.is_allowed("192.168.1.100")
        limiter.is_allowed("192.168.1.100")
        assert limiter.is_allowed("192.168.1.100") is False  # Bloqueada

        # IP-B: debería permitirse (contador independiente)
        assert limiter.is_allowed("192.168.1.200") is True
        assert limiter.is_allowed("192.168.1.200") is True
        assert limiter.is_allowed("192.168.1.200") is False  # Ahora IP-B bloqueada

    def test_rate_limiter_extracts_client_ip_from_x_forwarded_for(self):
        """AC-4: Extrae client_ip correcto del header X-Forwarded-For."""
        limiter = RateLimiter(requests=1, window_seconds=60)

        # X-Forwarded-For: client_ip, proxy_ip, cdn_ip
        # El limiter debe usar el PRIMER valor (client_ip real)
        client_ip = limiter.extract_client_ip(x_forwarded_for="203.0.113.1, 198.51.100.1, 192.0.2.1")
        assert client_ip == "203.0.113.1", "Should extract first IP (client IP)"

        # Verificar que el límite se aplica por client_ip, no por proxy
        assert limiter.is_allowed(client_ip) is True
        assert limiter.is_allowed(client_ip) is False  # Rate limited

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
