"""
FIX-REPAIR-003: Retry decorator con exponential backoff.

Usado por Google e EspoCRM para consistencia.
"""

import functools
import logging
import time
from typing import Callable, TypeVar, Any

logger = logging.getLogger(__name__)

T = TypeVar("T")


def retry(
    max_attempts: int = 3,
    backoff_base: float = 2.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,),
) -> Callable:
    """
    Decorator: retry con exponential backoff.

    Args:
        max_attempts: Máximo de intentos (default 3)
        backoff_base: Base para exponential backoff (default 2, so 2^1=2s, 2^2=4s, 2^3=8s)
        max_delay: Máximo delay entre intentos (default 60s)
        exceptions: Tuple de exceptions a retryear
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    # Don't retry after last attempt
                    if attempt >= max_attempts:
                        logger.exception(
                            f"Retry exhausted for {func.__name__} after {max_attempts} attempts"
                        )
                        raise

                    # Calculate backoff: 2^(attempt-1) = 2^0=1, 2^1=2, 2^2=4, etc.
                    # But we start from attempt=1, so: 2^1=2, 2^2=4, 2^3=8
                    delay = min(backoff_base ** attempt, max_delay)
                    logger.warning(
                        f"Retry {func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)

            # Should never reach here, but just in case
            raise last_exception

        return wrapper

    return decorator
