"""
Tests for input validation middleware (HU-031).
"""

import pytest


class TestInputValidationHU031:
    """HU-031: Input sanitization."""

    @pytest.fixture
    def validator(self):
        from agent.middleware.input_validator import InputValidator
        return InputValidator()

    def test_ac1_sql_injection_payload_blocked(self, validator):
        """AC-1: SQL injection payload detected and neutralized."""
        payload = "'; DROP TABLE cases; --"
        sanitized = validator.sanitize(payload)
        
        # Should remove dangerous characters
        assert "DROP TABLE" not in sanitized or ";" not in sanitized or "--" not in sanitized
        assert sanitized != payload

    def test_ac2_script_tag_blocked(self, validator):
        """AC-2: Script tags blocked."""
        payload = "<script>alert('xss')</script>"
        sanitized = validator.sanitize(payload)
        
        # Script tags should be removed
        assert "<script>" not in sanitized.lower()
        assert "</script>" not in sanitized.lower()

    def test_ac3_legitimate_message_allowed(self, validator):
        """AC-3: Legitimate messages pass through unchanged."""
        message = "Quiero saber el precio del módulo X"
        sanitized = validator.sanitize(message)
        
        assert sanitized == message

    def test_ac4_sql_keywords_in_context_allowed(self, validator):
        """AC-4: SQL keywords in normal context allowed."""
        messages = [
            "SELECT * FROM public_documentation",
            "WHERE can I find pricing?",
            "Use <name> format for submission"
        ]
        
        for msg in messages:
            sanitized = validator.sanitize(msg)
            # Should allow these contexts
            assert len(sanitized) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
