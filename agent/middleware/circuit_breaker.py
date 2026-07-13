"""Circuit breaker pattern for fault tolerance."""

import functools
import time
from typing import Any, Callable, Optional, Type, TypeVar

T = TypeVar("T")


class CircuitBreakerOpen(Exception):
    """Circuit breaker is open, rejecting calls."""

    pass


class CircuitBreaker:
    """Circuit breaker: CLOSED → OPEN → HALF_OPEN → CLOSED."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        expected_exception: Type[Exception] = Exception,
    ):
        """Initialize circuit breaker.

        Args:
            name: Service name for logging
            failure_threshold: Failures before opening
            recovery_timeout: Seconds in OPEN before HALF_OPEN
            expected_exception: Exception type to count as failure
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

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

                    # Failure in HALF_OPEN → reopen
                    if self.state == "half_open":
                        self.state = "open"

                raise

        return wrapper
