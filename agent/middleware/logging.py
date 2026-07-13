"""Structured logging with JSON output."""

import json
import logging
import sys
from typing import Any, Dict, List, Optional


def setup_structured_logging(
    level: str = "INFO",
    output: str = "stdout",
    secrets_to_scrub: Optional[List[str]] = None,
) -> logging.Logger:
    """Setup structured JSON logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        output: stdout or file
        secrets_to_scrub: List of environment variable names to hide

    Returns:
        Configured logger
    """
    if secrets_to_scrub is None:
        secrets_to_scrub = [
            "DATABASE_URL",
            "GOOGLE_APPLICATION_CREDENTIALS",
            "GOOGLE_OAUTH_TOKEN",
            "META_API_TOKEN",
            "FIREBIRD_PASSWORD",
        ]

    logger = logging.getLogger("bot")
    logger.setLevel(getattr(logging, level))

    handler = logging.StreamHandler(sys.stdout)
    formatter = JSONFormatter(secrets_to_scrub)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logs."""

    def __init__(self, secrets_to_scrub: List[str]):
        """Initialize formatter.

        Args:
            secrets_to_scrub: List of strings to redact
        """
        super().__init__()
        self.secrets_to_scrub = secrets_to_scrub

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }

        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        # Scrub secrets
        self._scrub_secrets(log_data)

        return json.dumps(log_data)

    def _scrub_secrets(self, data: Dict[str, Any]) -> None:
        """Scrub secrets from log data."""
        for key in self.secrets_to_scrub:
            if key in data:
                data[key] = "[REDACTED]"
            # Also check nested structures
            for k, v in data.items():
                if isinstance(v, dict):
                    if key in v:
                        v[key] = "[REDACTED]"
