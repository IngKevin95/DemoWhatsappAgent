"""Tests for audit logging."""

import pytest
from agent.middleware.audit_logger import AuditLogger


def test_audit_logger_init():
    """AuditLogger initializes with required fields."""
    logger = AuditLogger(
        tool_name="test_tool",
        user_phone="34912345678",
        trace_id="trace_123"
    )
    assert logger.tool_name == "test_tool"
    assert logger.user_phone == "34912345678"
    assert logger.trace_id == "trace_123"


def test_audit_logger_log_success():
    """AuditLogger logs successful operations."""
    logger = AuditLogger(
        tool_name="consultar_licencia",
        user_phone="34912345678"
    )
    # log_success should not raise an error
    logger.log_success(
        action="check_license",
        metadata={"licencia_id": "LIC-001"}
    )


def test_audit_logger_log_failure():
    """AuditLogger logs failures."""
    logger = AuditLogger(
        tool_name="agendar_cita",
        user_phone="34912345678"
    )
    # log_failure should not raise an error
    logger.log_failure(
        action="book_appointment",
        error="fecha_pasada"
    )
