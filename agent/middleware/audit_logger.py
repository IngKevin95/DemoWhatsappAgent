"""Audit logging for high-stakes tool operations."""

import functools
import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, Optional, TypeVar

T = TypeVar("T")

logger = logging.getLogger(__name__)


class AuditLogger:
    """Log tool operations to audit trail."""

    def __init__(
        self,
        tool_name: str,
        user_phone: str,
        trace_id: Optional[str] = None,
    ):
        """Initialize audit logger.

        Args:
            tool_name: Name of tool being called
            user_phone: User phone identifier
            trace_id: Optional trace ID for correlation
        """
        self.tool_name = tool_name
        self.user_phone = user_phone
        self.trace_id = trace_id

    def log_success(self, action: str, metadata: Optional[Dict[str, Any]] = None):
        """Log successful operation.

        Args:
            action: Action performed
            metadata: Additional metadata
        """
        if metadata is None:
            metadata = {}

        log_entry = {
            "user_phone": self.user_phone,
            "tool_name": self.tool_name,
            "action": action,
            "result": "success",
            "metadata": metadata,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if self.trace_id:
            log_entry["trace_id"] = self.trace_id

        logger.info(f"Audit: {action}", extra={"audit": log_entry})

    def log_failure(self, action: str, error: str):
        """Log failed operation.

        Args:
            action: Action attempted
            error: Error message
        """
        log_entry = {
            "user_phone": self.user_phone,
            "tool_name": self.tool_name,
            "action": action,
            "result": "failure",
            "error_message": error,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if self.trace_id:
            log_entry["trace_id"] = self.trace_id

        logger.error(f"Audit: {action} failed", extra={"audit": log_entry})


def audit_log(tool_name: str):
    """Decorator for audit logging.

    Args:
        tool_name: Name of the tool

    Returns:
        Decorator function
    """

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            # Extract user_phone from kwargs or assume it's the first arg
            user_phone = kwargs.get("user_phone", "unknown")
            if not user_phone and args:
                user_phone = args[0]

            auditor = AuditLogger(tool_name, user_phone)

            try:
                result = fn(*args, **kwargs)
                auditor.log_success("execution_completed")
                return result
            except Exception as e:
                auditor.log_failure("execution_failed", str(e))
                raise

        return wrapper

    return decorator
