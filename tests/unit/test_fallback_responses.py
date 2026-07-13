"""Tests for fallback responses when services are unavailable."""

import pytest
from agent.middleware.fallback import get_fallback, FALLBACK_RESPONSES


def test_fallback_gemini_timeout():
    """Fallback response for Gemini timeout."""
    response = get_fallback("gemini", "timeout", "34912345678")
    assert isinstance(response, str)
    assert len(response) > 0


def test_fallback_google_calendar_error():
    """Fallback response for Google Calendar error."""
    response = get_fallback("google_calendar", "error")
    assert isinstance(response, str)
    assert "agend" in response.lower() or "disponible" in response.lower()


def test_fallback_espocrm_escalation():
    """Fallback response for EspoCRM escalation failure."""
    response = get_fallback("espocrm", "escalation_fail")
    assert isinstance(response, str)
    assert "agente" in response.lower() or "contactar" in response.lower()


def test_fallback_firebird_error():
    """Fallback response for Firebird error."""
    response = get_fallback("firebird", "error")
    assert isinstance(response, str)


def test_fallback_unknown_service():
    """Unknown service returns default fallback."""
    response = get_fallback("unknown", "unknown_error")
    assert response == "Intenta más tarde, por favor."
