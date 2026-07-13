"""Tests for circuit breaker pattern."""

import pytest
from agent.middleware.circuit_breaker import CircuitBreaker, CircuitBreakerOpen


def test_circuit_breaker_allows_calls_when_closed():
    """CLOSED: calls pass through normally."""
    breaker = CircuitBreaker("test", failure_threshold=3, recovery_timeout=1)

    result = breaker(lambda: "success")()

    assert result == "success"


def test_circuit_breaker_opens_after_threshold_failures():
    """OPEN: after N failures, circuit opens."""
    breaker = CircuitBreaker("test", failure_threshold=2, recovery_timeout=1)

    def failing_fn():
        raise ConnectionError("Service down")

    # First failure
    with pytest.raises(ConnectionError):
        breaker(failing_fn)()

    # Second failure → should open
    with pytest.raises(ConnectionError):
        breaker(failing_fn)()

    # Verify circuit is now OPEN
    assert breaker.state == "open"


def test_circuit_breaker_fails_fast_when_open():
    """OPEN: all calls fail immediately with CircuitBreakerOpen."""
    breaker = CircuitBreaker("test", failure_threshold=1, recovery_timeout=1)

    def failing_fn():
        raise ConnectionError("Service down")

    # Trigger open
    with pytest.raises(ConnectionError):
        breaker(failing_fn)()

    # Now circuit is OPEN; next call should fail fast
    with pytest.raises(CircuitBreakerOpen):
        breaker(lambda: "this should not run")()


def test_circuit_breaker_half_open_after_timeout():
    """HALF_OPEN: after timeout, allow one test call."""
    import time

    breaker = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1)

    call_count = [0]

    def fn():
        call_count[0] += 1
        if call_count[0] <= 1:
            raise ConnectionError("Fail once")
        return "recovered"

    # Trigger open
    with pytest.raises(ConnectionError):
        breaker(fn)()

    # Wait for timeout and call again
    time.sleep(0.2)

    # Call should succeed now (after recovery timeout)
    result = breaker(fn)()
    assert result == "recovered"


def test_circuit_breaker_half_open_success_closes():
    """HALF_OPEN + success: circuit closes."""
    import time

    breaker = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1)

    call_count = [0]

    def fn():
        call_count[0] += 1
        if call_count[0] <= 1:
            raise ConnectionError("Fail")
        return "ok"

    # Trigger open
    with pytest.raises(ConnectionError):
        breaker(fn)()

    assert breaker.state == "open"

    # Wait for recovery timeout
    time.sleep(0.2)

    # Call in HALF_OPEN state → should succeed and close
    result = breaker(fn)()

    assert result == "ok"
    assert breaker.state == "closed"


def test_circuit_breaker_half_open_failure_reopens():
    """HALF_OPEN + failure: circuit reopens."""
    import time

    breaker = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1)

    call_count = [0]

    def fn():
        call_count[0] += 1
        raise ConnectionError("Still down")

    # Trigger open
    with pytest.raises(ConnectionError):
        breaker(fn)()

    # Wait for recovery timeout
    time.sleep(0.2)

    # Call fails in HALF_OPEN → reopens (circuit open again)
    with pytest.raises(ConnectionError):
        breaker(fn)()

    # Next immediate call should fail with CircuitBreakerOpen (not ConnectionError)
    # because circuit reopened
    with pytest.raises(CircuitBreakerOpen):
        breaker(fn)()


def test_circuit_breaker_respects_exception_types():
    """Only fail-count on expected exceptions."""
    breaker = CircuitBreaker(
        "test",
        failure_threshold=2,
        recovery_timeout=1,
        expected_exception=ConnectionError
    )

    # ValueError should not count as failure
    with pytest.raises(ValueError):
        breaker(lambda: (_ for _ in ()).throw(ValueError("Not retryable")))()

    # Circuit should still be CLOSED
    assert breaker.state == "closed"

    # ConnectionError counts
    with pytest.raises(ConnectionError):
        breaker(lambda: (_ for _ in ()).throw(ConnectionError("Fail")))()

    with pytest.raises(ConnectionError):
        breaker(lambda: (_ for _ in ()).throw(ConnectionError("Fail")))()

    # Now OPEN
    assert breaker.state == "open"


def test_circuit_breaker_metrics():
    """Metrics are tracked."""
    breaker = CircuitBreaker("test", failure_threshold=2, recovery_timeout=1)

    assert breaker.failure_count == 0

    def fn():
        raise ConnectionError("Fail")

    with pytest.raises(ConnectionError):
        breaker(fn)()

    assert breaker.failure_count == 1

    with pytest.raises(ConnectionError):
        breaker(fn)()

    assert breaker.failure_count == 2
    assert breaker.state == "open"
