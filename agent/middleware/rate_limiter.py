"""
Rate limiting middleware for webhook protection against DDoS.

Implements sliding window algorithm to limit requests per IP.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter using sliding window algorithm.

    Limits requests to max_requests per window_seconds for each IP.
    """

    def __init__(self, requests: int = 10, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            requests: Maximum requests allowed in window (default: 10)
            window_seconds: Time window in seconds (default: 60)
        """
        self.requests = requests
        self.window_seconds = window_seconds
        self._request_times: Dict[str, List[float]] = {}  # IP -> [timestamps]

    def is_allowed(self, ip: str) -> bool:
        """
        Check if request from IP is allowed.

        Args:
            ip: Client IP address

        Returns:
            True if request is allowed, False if rate limited
        """
        current_time = time.time()

        # Get timestamps for this IP
        if ip not in self._request_times:
            self._request_times[ip] = []

        timestamps = self._request_times[ip]

        # Remove old requests outside the window
        cutoff_time = current_time - self.window_seconds
        timestamps[:] = [t for t in timestamps if t > cutoff_time]

        # Check if limit exceeded
        if len(timestamps) >= self.requests:
            logger.warning(
                f"Rate limit exceeded for {ip}: {len(timestamps) + 1} requests in {self.window_seconds}s"
            )
            return False

        # Record this request
        timestamps.append(current_time)
        return True

    def _reset_stale_entries(self, current_time: datetime = None):
        """
        Remove IPs with no recent requests (cleanup).

        Args:
            current_time: Current time for testing (default: now)
        """
        if current_time is None:
            current_time = datetime.now()

        current_timestamp = current_time.timestamp()
        cutoff_time = current_timestamp - self.window_seconds

        # Remove entries where all timestamps are old
        ips_to_remove = []
        for ip, timestamps in self._request_times.items():
            timestamps[:] = [t for t in timestamps if t > cutoff_time]
            if not timestamps:
                ips_to_remove.append(ip)

        for ip in ips_to_remove:
            del self._request_times[ip]

    def extract_client_ip(self, x_forwarded_for: str = None, socket_ip: str = None) -> str:
        """
        Extract real client IP from X-Forwarded-For header or socket.

        X-Forwarded-For format: client_ip, proxy1_ip, proxy2_ip
        Uses first IP (leftmost) as the real client.

        Args:
            x_forwarded_for: X-Forwarded-For header value
            socket_ip: Direct socket IP (fallback)

        Returns:
            Extracted client IP
        """
        if x_forwarded_for:
            # Extract first IP from X-Forwarded-For chain
            ips = [ip.strip() for ip in x_forwarded_for.split(',')]
            if ips:
                return ips[0]

        return socket_ip or "unknown"
