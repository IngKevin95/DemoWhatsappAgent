"""Tests for structured logging with secrets scrubbing."""

import pytest
import logging
import json
from agent.middleware.logging import setup_structured_logging, JSONFormatter


def test_json_formatter_basic():
    """JSONFormatter produces valid JSON output."""
    formatter = JSONFormatter(["DATABASE_URL"])
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    output = formatter.format(record)
    assert isinstance(output, str)
    # Should be valid JSON
    data = json.loads(output)
    assert "Test message" in data.get("message", "")


def test_secrets_scrubbed():
    """Secrets are scrubbed from logs."""
    formatter = JSONFormatter(["DATABASE_URL"])
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Connection settings",
        args=(),
        exc_info=None
    )
    # Add extra attribute with secret
    record.extra = {"DATABASE_URL": "postgresql://user:password@localhost/db"}
    output = formatter.format(record)
    data = json.loads(output)
    # DATABASE_URL should be redacted in extra field
    assert data.get("extra", {}).get("DATABASE_URL") == "[REDACTED]" or "redacted" in output.lower()


def test_setup_structured_logging():
    """Setup returns logger instance."""
    logger = setup_structured_logging()
    assert isinstance(logger, logging.Logger)
    assert logger.name == "bot"
