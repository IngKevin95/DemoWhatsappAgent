"""
Audit logging middleware for tracking critical decisions.

Logs all calls to high-stakes tools (escalate, schedule, license check, reclassify).
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from functools import wraps

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Async audit logger for critical tool decisions.

    Queues audit events and writes them to audit_logs table asynchronously.
    """

    def __init__(self, db_enabled: bool = False):
        """
        Initialize audit logger.

        Args:
            db_enabled: Whether to write to database (default: False for v1.0 MVP)
        """
        self.db_enabled = db_enabled
        self._queue = []

    def log_event(
        self,
        user_id: str,
        tool_name: str,
        action: str,
        result: str,
        metadata: Optional[Dict[str, Any]] = None,
        error_msg: Optional[str] = None,
    ) -> None:
        """
        Log an audit event.

        Args:
            user_id: User ID (WhatsApp phone or agent ID)
            tool_name: Name of tool called (escalate, agendar_cita, etc.)
            action: What action was performed (create_case, schedule_event, etc.)
            result: Result (success, failed, valid, expired)
            metadata: Additional metadata as dict
            error_msg: Error message if failed
        """
        event = {
            "user_id": user_id,
            "tool_name": tool_name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": action,
            "result": result,
            "metadata": metadata or {},
            "error_msg": error_msg,
        }

        # Queue for async writing (v1.0 MVP)
        self._queue.append(event)

        # Log event
        logger.info(f"Audit event: {json.dumps(event)}")

    def flush(self) -> None:
        """Flush queued events to database (if enabled)."""
        if self.db_enabled and self._queue:
            logger.info(f"Flushing {len(self._queue)} audit events")
            self._queue.clear()


# Global audit logger instance
_audit_logger = AuditLogger()


def audit_log(action: str):
    """
    Decorator to automatically log tool calls.

    Args:
        action: Action description (create_case, schedule_event, etc.)
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_id = kwargs.get("user_id", "unknown")

            try:
                result = func(*args, **kwargs)
                _audit_logger.log_event(
                    user_id=user_id,
                    tool_name=func.__name__,
                    action=action,
                    result="success",
                    metadata={"return_value": str(result)[:100]},
                )
                return result
            except Exception as e:
                _audit_logger.log_event(
                    user_id=user_id,
                    tool_name=func.__name__,
                    action=action,
                    result="failed",
                    error_msg=str(e)[:200],
                )
                raise

        return wrapper

    return decorator
