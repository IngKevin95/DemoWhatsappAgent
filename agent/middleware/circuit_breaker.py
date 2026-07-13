"""Circuit breaker pattern for fault tolerance."""

import functools
import os
import time
from typing import Any, Callable, Optional, Type, TypeVar

T = TypeVar("T")


class CircuitBreakerOpen(Exception):
    """Circuit breaker is open, rejecting calls."""

    pass


class CircuitBreaker:
    """Circuit breaker: CLOSED → OPEN → HALF_OPEN → CLOSED.

    FIX-REPAIR-002: Added fallback support for Gemini integration."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = None,
        recovery_timeout: int = None,
        expected_exception: Type[Exception] = Exception,
        fallback_fn: Optional[Callable] = None,
    ):
        """Initialize circuit breaker.

        Args:
            name: Service name for logging
            failure_threshold: Failures before opening (from env CIRCUIT_BREAKER_THRESHOLD or 3)
            recovery_timeout: Seconds in OPEN before HALF_OPEN (from env or 30)
            expected_exception: Exception type to count as failure
            fallback_fn: Function to call if circuit open (instead of raising exception)
        """
        self.name = name
        # FIX-REPAIR-002: Load from env if not provided
        self.failure_threshold = failure_threshold or int(os.getenv('CIRCUIT_BREAKER_THRESHOLD', '3'))
        self.recovery_timeout = recovery_timeout or int(os.getenv('CIRCUIT_BREAKER_WINDOW_SEC', '30'))
        self.expected_exception = expected_exception
        self.fallback_fn = fallback_fn

        self.state = "closed"  # CLOSED, OPEN, HALF_OPEN
        self.failure_count = 0
        self.last_failure_time = None

    def _update_state(self):
        """Update state based on timeout (OPEN → HALF_OPEN)."""
        if self.state == "open":
            if (
                self.last_failure_time
                and time.time() - self.last_failure_time > self.recovery_timeout
            ):
                self.state = "half_open"

    def __call__(self, fn: Callable[..., T]) -> Callable[..., T]:
        """Wrap a function with circuit breaker."""

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            self._update_state()

            if self.state == "open":
                # FIX-REPAIR-002: Return fallback if available, else raise
                if self.fallback_fn:
                    return self.fallback_fn(*args, **kwargs)
                raise CircuitBreakerOpen(f"Circuit breaker {self.name} is open")

            try:
                result = fn(*args, **kwargs)

                # Success in HALF_OPEN → close circuit
                if self.state == "half_open":
                    self.state = "closed"
                    self.failure_count = 0

                return result

            except Exception as e:
                if isinstance(e, self.expected_exception):
                    self.failure_count += 1
                    self.last_failure_time = time.time()

                    if self.failure_count >= self.failure_threshold:
                        self.state = "open"
                        # FIX-REPAIR-002: Return fallback when opening circuit
                        if self.fallback_fn:
                            return self.fallback_fn(*args, **kwargs)

                    # Failure in HALF_OPEN → reopen
                    if self.state == "half_open":
                        self.state = "open"

                raise

        return wrapper
