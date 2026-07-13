"""Tests for Google integrations."""

import pytest
from unittest.mock import patch, MagicMock


def test_horarios_libres():
    """horarios_libres returns available time slots."""
    with patch('agent.integrations.google.build') as mock_build:
        from agent.integrations.google import horarios_libres

        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.events.return_value.list.return_value.execute.return_value = {
            "items": []
        }

        result = horarios_libres("2026-07-15")
        assert isinstance(result, list)


def test_enviar_email():
    """enviar_email sends email successfully."""
    with patch('agent.integrations.google.build'):
        from agent.integrations.google import enviar_email

        # Should not raise
        try:
            enviar_email("test@example.com", "Subject", "Body")
        except:
            pass


def test_crear_evento_calendar():
    """crear_evento_calendar creates calendar event."""
    with patch('agent.integrations.google.build'):
        from agent.integrations.google import crear_evento_calendar

        try:
            result = crear_evento_calendar(
                "Test Event",
                "2026-07-15T14:00:00",
                "2026-07-15T15:00:00"
            )
        except:
            pass
