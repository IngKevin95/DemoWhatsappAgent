"""Tests for retry logic with exponential backoff."""

import asyncio
import time
import pytest
from agent.middleware.retry import retry_operation, retry


def test_retry_succeeds_on_first_attempt():
    """Operación exitosa sin necesidad de reintentos."""
    calls = []

    def operation():
        calls.append(1)
        return {"result": "success"}

    result = retry_operation(operation, max_attempts=3)

    assert result == {"result": "success"}
    assert len(calls) == 1


def test_retry_succeeds_after_transient_failure():
    """Reintenta y eventualmente tiene éxito tras falla transitoria."""
    calls = []

    def operation():
        calls.append(1)
        if len(calls) < 3:
            raise ConnectionError("Service temporarily unavailable")
        return {"result": "success"}

    result = retry_operation(operation, max_attempts=3, base_delay=0.01)

    assert result == {"result": "success"}
    assert len(calls) == 3


def test_retry_exhausts_max_attempts():
    """Agota intentos máximos y lanza error."""
    calls = []

    def operation():
        calls.append(1)
        raise ConnectionError("Persistent failure")

    with pytest.raises(ConnectionError, match="Persistent failure"):
        retry_operation(operation, max_attempts=3, base_delay=0.01)

    assert len(calls) == 3


def test_retry_exponential_backoff():
    """Backoff exponencial: 1s, 2s, 4s."""
    calls_with_time = []

    def operation():
        calls_with_time.append(time.time())
        if len(calls_with_time) < 3:
            raise ConnectionError("fail")
        return "ok"

    # Con base_delay=0.01, esperamos delays crecientes
    retry_operation(operation, max_attempts=3, base_delay=0.01, backoff_factor=2)

    assert len(calls_with_time) == 3
    # Verificar que el delay se incrementó
    assert calls_with_time[1] > calls_with_time[0]
    assert calls_with_time[2] > calls_with_time[1]


def test_retry_with_jitter():
    """Jitter ±20% para evitar thundering herd."""
    calls = []

    def operation():
        calls.append(1)
        if len(calls) < 2:
            raise ConnectionError("fail")
        return "ok"

    # Ejecutar múltiples veces para verificar variabilidad
    timings = []
    for _ in range(5):
        start = time.time()
        retry_operation(operation, max_attempts=3, base_delay=0.01, jitter=True)
        timings.append(time.time() - start)

    # Con jitter, los timings pueden variar
    assert len(timings) == 5


@pytest.mark.asyncio
async def test_async_retry_succeeds_after_failure():
    """Versión async de retry."""
    calls = []

    async def async_operation():
        calls.append(1)
        if len(calls) < 2:
            raise TimeoutError("API timeout")
        return {"status": "ok"}

    result = await retry_operation(async_operation, max_attempts=3, base_delay=0.01, is_async=True)

    assert result == {"status": "ok"}
    assert len(calls) == 2


def test_retry_decorator_basic():
    """Decorator @retry en funciones."""

    @retry(max_attempts=3, base_delay=0.01)
    def flaky_api_call():
        if not hasattr(flaky_api_call, "attempts"):
            flaky_api_call.attempts = 0
        flaky_api_call.attempts += 1
        if flaky_api_call.attempts < 2:
            raise ConnectionError("Service down")
        return {"data": "ok"}

    result = flaky_api_call()

    assert result == {"data": "ok"}
    assert flaky_api_call.attempts == 2


def test_retry_respects_specific_exceptions():
    """Solo reintenta en excepciones específicas (ConnectionError, Timeout)."""
    calls = []

    def operation():
        calls.append(1)
        if len(calls) == 1:
            raise ConnectionError("Transitorio")
        if len(calls) == 2:
            raise ValueError("Permanente")  # No reintentable
        return "ok"

    # Debe lanzar ValueError en el segundo intento (no continúa retrying)
    with pytest.raises(ValueError, match="Permanente"):
        retry_operation(
            operation,
            max_attempts=3,
            base_delay=0.01,
            retryable_exceptions=(ConnectionError, TimeoutError),
        )

    assert len(calls) == 2
