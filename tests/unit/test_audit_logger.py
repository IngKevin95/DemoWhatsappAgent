import pytest
from unittest.mock import patch, MagicMock
from agent.middleware.audit_logger import AuditLogger, audit_log, _audit_logger

class TestAuditLogger:

    def setup_method(self):
        self.logger = AuditLogger(db_enabled=False)

    def test_log_event_adds_to_queue(self):
        self.logger.log_event("user1", "test_tool", "test_action", "success")
        assert len(self.logger._queue) == 1
        event = self.logger._queue[0]
        assert event["user_id"] == "user1"
        assert event["tool_name"] == "test_tool"
        assert event["action"] == "test_action"
        assert event["result"] == "success"
        assert "timestamp" in event
        assert event["metadata"] == {}
        assert event["error_msg"] is None

    def test_log_event_with_metadata_and_error(self):
        self.logger.log_event(
            user_id="user2",
            tool_name="test_tool2",
            action="test_action2",
            result="failed",
            metadata={"key": "value"},
            error_msg="some error"
        )
        assert len(self.logger._queue) == 1
        event = self.logger._queue[0]
        assert event["metadata"] == {"key": "value"}
        assert event["error_msg"] == "some error"

    def test_flush_disabled(self):
        self.logger.log_event("user1", "test_tool", "test_action", "success")
        self.logger.flush()
        assert len(self.logger._queue) == 1  # Queue is not cleared when disabled

    def test_flush_enabled(self):
        self.logger.db_enabled = True
        self.logger.log_event("user1", "test_tool", "test_action", "success")
        self.logger.flush()
        assert len(self.logger._queue) == 0  # Queue is cleared

class TestAuditLogDecorator:
    
    def setup_method(self):
        _audit_logger._queue.clear()
        _audit_logger.db_enabled = False

    def test_decorator_success(self):
        @audit_log("test_action")
        def dummy_function(user_id):
            return "ok"

        res = dummy_function(user_id="user123")
        assert res == "ok"
        assert len(_audit_logger._queue) == 1
        event = _audit_logger._queue[0]
        assert event["user_id"] == "user123"
        assert event["tool_name"] == "dummy_function"
        assert event["action"] == "test_action"
        assert event["result"] == "success"

    def test_decorator_failure(self):
        @audit_log("test_action")
        def dummy_fail(user_id):
            raise ValueError("bad input")

        with pytest.raises(ValueError):
            dummy_fail(user_id="user123")
        
        assert len(_audit_logger._queue) == 1
        event = _audit_logger._queue[0]
        assert event["user_id"] == "user123"
        assert event["tool_name"] == "dummy_fail"
        assert event["result"] == "failed"
        assert "bad input" in event["error_msg"]

    def test_decorator_no_user_id(self):
        @audit_log("test_action")
        def dummy_no_user():
            return "ok"

        dummy_no_user()
        assert len(_audit_logger._queue) == 1
        event = _audit_logger._queue[0]
        assert event["user_id"] == "unknown"
