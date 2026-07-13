"""Retry logic with exponential backoff."""

import asyncio
import functools
import random
import time
from typing import Any, Callable, Coroutine, Optional, Tuple, TypeVar, Union

T = TypeVar("T")

# Default retryable exceptions
DEFAULT_RETRYABLE = (ConnectionError, TimeoutError)


def retry_operation(
    fn: Union[Callable[[], T], Callable[[], Coroutine[Any, Any, T]]],
    max_attempts: int = 3,
    base_delay: float = 1,
    backoff_factor: float = 2,
    jitter: bool = True,
    retryable_exceptions: Tuple[type, ...] = DEFAULT_RETRYABLE,
    is_async: bool = False,
):
    """Retry operation with exponential backoff.

    Args:
        fn: Callable to retry (sync or async)
        max_attempts: Total attempts (including first)
        base_delay: Initial delay in seconds
        backoff_factor: Multiplier for exponential backoff
        jitter: Add ±20% random jitter
        retryable_exceptions: Exception types to retry on
        is_async: True if fn is async

    Returns:
        Result of fn

    Raises:
        Last exception if all attempts exhausted
    """
    if is_async:
        return _retry_async(fn, max_attempts, base_delay, backoff_factor, jitter, retryable_exceptions)
    else:
        return _retry_sync(fn, max_attempts, base_delay, backoff_factor, jitter, retryable_exceptions)


def _retry_sync(fn, max_attempts, base_delay, backoff_factor, jitter, retryable_exceptions):
    """Sync retry implementation."""
    last_exception = None

    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as e:
            if not isinstance(e, retryable_exceptions):
                raise

            last_exception = e

            if attempt < max_attempts - 1:
                # Calculate delay
                delay = base_delay * (backoff_factor ** attempt)
                if jitter:
                    jitter_amount = delay * 0.2 * random.random()
                    delay = delay - (delay * 0.2) + jitter_amount

                time.sleep(delay)

    if last_exception:
        raise last_exception
    return None


async def _retry_async(fn, max_attempts, base_delay, backoff_factor, jitter, retryable_exceptions):
    """Async retry implementation."""
    last_exception = None

    for attempt in range(max_attempts):
        try:
            return await fn()
        except Exception as e:
            if not isinstance(e, retryable_exceptions):
                raise

            last_exception = e

            if attempt < max_attempts - 1:
                # Calculate delay
                delay = base_delay * (backoff_factor ** attempt)
                if jitter:
                    jitter_amount = delay * 0.2 * random.random()
                    delay = delay - (delay * 0.2) + jitter_amount

                await asyncio.sleep(delay)

    if last_exception:
        raise last_exception
    return None


def retry(
    max_attempts: int = 3,
    base_delay: float = 1,
    backoff_factor: float = 2,
    jitter: bool = True,
    retryable_exceptions: Tuple[type, ...] = DEFAULT_RETRYABLE,
):
    """Decorator for retry logic."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            return retry_operation(
                lambda: fn(*args, **kwargs),
                max_attempts=max_attempts,
                base_delay=base_delay,
                backoff_factor=backoff_factor,
                jitter=jitter,
                retryable_exceptions=retryable_exceptions,
                is_async=False,
            )

        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            return await retry_operation(
                lambda: fn(*args, **kwargs),
                max_attempts=max_attempts,
                base_delay=base_delay,
                backoff_factor=backoff_factor,
                jitter=jitter,
                retryable_exceptions=retryable_exceptions,
                is_async=True,
            )

        # Return appropriate wrapper based on whether fn is async
        if asyncio.iscoroutinefunction(fn):
            return async_wrapper
        else:
            return wrapper

    return decorator
