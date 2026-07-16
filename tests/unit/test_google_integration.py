"""Tests for Google integrations."""

import pytest
from unittest.mock import patch, MagicMock


def test_horarios_libres_generacion_dinamica():
    """horarios_libres genera bloques de 1 hora dinámicamente basados en hora_inicio y hora_fin."""
    with patch('agent.integrations.google.get_calendar_service') as mock_service_fn:
        from agent.integrations.google import horarios_libres

        mock_service = MagicMock()
        mock_service_fn.return_value = mock_service
        # Sin eventos ocupados
        mock_service.freebusy.return_value.query.return_value.execute.return_value = {
            "calendars": {
                "primary": {
                    "busy": []
                }
            }
        }

        result = horarios_libres("2026-07-15", hora_inicio="09:00", hora_fin="12:00")
        assert result == ["09:00", "10:00", "11:00"]


def test_horarios_libres_con_conflictos():
    """horarios_libres excluye bloques que chocan con eventos ocupados del calendario."""
    with patch('agent.integrations.google.get_calendar_service') as mock_service_fn:
        from agent.integrations.google import horarios_libres

        mock_service = MagicMock()
        mock_service_fn.return_value = mock_service
        # Evento ocupado de 10:15 a 11:30 (debería bloquear los slots de 10:00 y 11:00)
        mock_service.freebusy.return_value.query.return_value.execute.return_value = {
            "calendars": {
                "primary": {
                    "busy": [
                        {"start": "2026-07-15T10:15:00", "end": "2026-07-15T11:30:00"}
                    ]
                }
            }
        }

        result = horarios_libres("2026-07-15", hora_inicio="09:00", hora_fin="13:00")
        # 09:00 a 10:00 (Libre)
        # 10:00 a 11:00 (Bloqueado)
        # 11:00 a 12:00 (Bloqueado)
        # 12:00 a 13:00 (Libre)
        assert result == ["09:00", "12:00"]


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
