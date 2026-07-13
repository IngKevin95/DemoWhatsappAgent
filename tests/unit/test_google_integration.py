"""Tests for Google integrations."""

import pytest
from unittest.mock import patch, MagicMock


def test_horarios_libres():
    """horarios_libres returns available time slots."""
    with patch('agent.integrations.google.get_calendar_service') as mock_service_fn:
        from agent.integrations.google import horarios_libres

        mock_service = MagicMock()
        mock_service_fn.return_value = mock_service
        mock_service.freebusy.return_value.query.return_value.execute.return_value = {
            "calendars": {
                "primary": {
                    "busy": []
                }
            }
        }

        result = horarios_libres("2026-07-15")
        assert isinstance(result, list)


def test_enviar_email():
    """enviar_email sends email successfully."""
    with patch('agent.integrations.google.get_gmail_service') as mock_service_fn:
        from agent.integrations.google import enviar_email

        mock_service = MagicMock()
        mock_service_fn.return_value = mock_service
        mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
            "id": "123"
        }

        result = enviar_email("test@example.com", "Subject", "Body")
        assert isinstance(result, dict)


def test_crear_evento_calendar():
    """crear_evento_calendar creates calendar event."""
    with patch('agent.integrations.google.get_calendar_service') as mock_service_fn:
        from agent.integrations.google import crear_evento_calendar

        mock_service = MagicMock()
        mock_service_fn.return_value = mock_service
        mock_service.events.return_value.insert.return_value.execute.return_value = {
            "id": "event123"
        }

        result = crear_evento_calendar(
            "Test",
            "34912345678",
            "Test meeting",
            "2026-07-15",
            "14:00"
        )
        assert isinstance(result, dict)
