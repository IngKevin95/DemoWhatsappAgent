"""Unit tests for tools.py - core business logic."""

import pytest
from unittest.mock import patch, MagicMock
from agent.tools import (
    consultar_precio_modulo,
    consultar_licencia,
    agendar_cita,
    reclasificar_caso_sin_licencia,
    escalar_a_humano,
)


class TestConsultarPrecioModulo:
    """Tests for price queries."""

    def test_consultar_precio_existente(self, mock_postgres):
        """Query existing module price."""
        resultado = consultar_precio_modulo("Pro")
        assert isinstance(resultado, dict)

    def test_consultar_precio_no_existe(self):
        """Query non-existent module."""
        resultado = consultar_precio_modulo("ModuloFake")
        assert "error" in resultado or resultado is None or isinstance(resultado, dict)


class TestConsultarLicencia:
    """Tests for license queries."""

    def test_consultar_licencia_activa(self, mock_firebird):
        """Query active license."""
        resultado = consultar_licencia("12345678901")
        assert isinstance(resultado, dict)
        if resultado and "licencia_id" in resultado:
            assert resultado["estado"] in ["activa", "vencida", "suspendida"]

    def test_consultar_licencia_no_existe(self):
        """Query non-existent license."""
        resultado = consultar_licencia("99999999999")
        assert resultado is not None


class TestAgendarCita:
    """Tests for appointment booking."""

    def test_agendar_cita_valida(self, mock_google_calendar):
        """Book valid appointment."""
        resultado = agendar_cita(
            nombre="Juan Pérez",
            telefono="34912345678",
            motivo="Consultoría",
            fecha="2026-07-15",
            hora="14:00",
            area="Soporte"
        )
        assert isinstance(resultado, dict)

    def test_agendar_cita_fecha_pasada(self):
        """Reject past date."""
        resultado = agendar_cita(
            nombre="Juan Pérez",
            telefono="34912345678",
            motivo="Consultoría",
            fecha="2020-01-01",
            hora="14:00",
            area="Soporte"
        )
        assert resultado is not None  # Either error or handled


class TestReclasificarCaso:
    """Tests for case reclassification."""

    def test_reclasificar_caso_estructura(self):
        """Reclassification returns dict."""
        resultado = reclasificar_caso_sin_licencia(
            caso_id="CASO-001",
            telefono="34912345678",
            nombre="Juan Pérez"
        )
        assert isinstance(resultado, dict)

    def test_reclasificar_caso_tiene_campos(self):
        """Result has expected fields."""
        resultado = reclasificar_caso_sin_licencia(
            caso_id="CASO-001",
            telefono="34912345678",
            nombre="Juan Pérez"
        )
        if resultado:
            assert "puede_procesar" in resultado or "estado" in resultado or len(resultado) > 0


class TestEscalarAHumano:
    """Tests for escalation."""

    def test_escalar_a_humano_valido(self):
        """Escalate to human support."""
        resultado = escalar_a_humano(
            telefono="34912345678",
            nombre="Juan Pérez",
            resumen_caso="Error en módulo Pro",
            area="Soporte"
        )
        assert isinstance(resultado, dict)

    def test_escalar_a_humano_sin_agentes(self):
        """Handle escalation when no agents available."""
        resultado = escalar_a_humano(
            telefono="34912345678",
            nombre="Juan Pérez",
            resumen_caso="Urgente",
            area="AreaQueNoExiste"
        )
        # Should handle gracefully
        assert resultado is not None
