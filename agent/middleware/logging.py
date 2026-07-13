"""Structured logging with JSON output."""

import json
import logging
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


class TokenSanitizer:
    """FIX-REPAIR-001: Redacta tokens, credentials de strings."""

    PATTERNS: List[Tuple[str, str]] = [
        (r"(?i)(authorization|bearer)[\s:]*([a-zA-Z0-9\-._~+/]+=*)", r"\1: [REDACTED]"),
        (r"(?i)(access_token|refresh_token)[\s:]*([^\s,\n]+)", r"\1: [REDACTED]"),
        (r"(?i)(sk-proj-[a-zA-Z0-9\-._]+)", "[REDACTED]"),
        (r"(?i)(ya29\.[a-zA-Z0-9\-_]+)", "[REDACTED]"),
        (r"(?i)(database_url|db_url)[\s:=]*([^\s\n]+)", r"\1: [REDACTED]"),
        (r"(?i)(postgresql|mysql|mongodb)://([^/@\s]+):([^/@\s]+)@", r"\1://[REDACTED]:[REDACTED]@"),
        (r"(?i)(api_key|apikey|secret_key)[\s:=]*([^\s,\n]+)", r"\1: [REDACTED]"),
        (r"(?i)(password)[\s:=]*([^\s,\n]+)", r"\1: [REDACTED]"),
    ]

    @classmethod
    def sanitize(cls, text: str) -> str:
        """Redacta credentials en text."""
        if not text:
            return text
        sanitized = text
        for pattern, replacement in cls.PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized)
        return sanitized


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
        msg = record.getMessage()
        # FIX-REPAIR-001: Sanitize tokens/credentials in message
        msg = TokenSanitizer.sanitize(msg)

        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": msg,
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
