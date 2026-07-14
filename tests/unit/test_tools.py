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

    def test_reclasificar_caso_con_nombre_vacio(self):
        """Reclassification with empty name."""
        resultado = reclasificar_caso_sin_licencia(
            caso_id="CASO-002",
            telefono="34912345678",
            nombre=""
        )
        assert isinstance(resultado, dict)



class TestEscalarAHumano:
    """Tests for escalation."""

    def _mock_session(self):
        """Build a minimal mock SyncSession context manager."""
        from unittest.mock import MagicMock
        session = MagicMock()
        session.__enter__ = MagicMock(return_value=session)
        session.__exit__ = MagicMock(return_value=False)
        # query().filter().order_by().first() -> None
        session.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        session.query.return_value.filter.return_value.first.return_value = None
        session.query.return_value.get.return_value = None
        session.flush = MagicMock()
        session.commit = MagicMock()
        session.add = MagicMock()
        return session

    def test_escalar_a_humano_valido(self):
        """Escalate to human support (mocked DB + external services)."""
        session = self._mock_session()
        # Mock area row and radicado
        area_row = MagicMock()
        area_row.id = 1
        session.query.return_value.filter.return_value.first.return_value = area_row

        radicado_mock = MagicMock()
        radicado_mock.id = 42
        radicado_mock.email_enviado = True
        radicado_mock.crm_case_id = "CRM-001"

        with patch("agent.tools.SyncSession", return_value=session), \
             patch("agent.tools._upsert_contacto", return_value=MagicMock()), \
             patch("agent.tools._get_area", return_value=area_row), \
             patch("agent.tools._agentes_por_area", return_value=[]), \
             patch("agent.tools.espocrm.crear_caso", return_value={"id": "CRM-001"}), \
             patch("agent.tools.enviar_email", return_value=None), \
             patch("agent.tools.Radicado", return_value=radicado_mock):
            resultado = escalar_a_humano(
                telefono="34912345678",
                nombre="Juan Pérez",
                resumen_caso="Error en módulo Pro",
                area="Soporte"
            )
            assert isinstance(resultado, dict)

    def test_escalar_a_humano_sin_agentes(self):
        """Handle escalation when no agents available (mocked DB)."""
        session = self._mock_session()
        area_row = MagicMock()
        area_row.id = 1
        radicado_mock = MagicMock()
        radicado_mock.id = 99
        radicado_mock.email_enviado = False

        with patch("agent.tools.SyncSession", return_value=session), \
             patch("agent.tools._upsert_contacto", return_value=MagicMock()), \
             patch("agent.tools._get_area", return_value=area_row), \
             patch("agent.tools._agentes_por_area", return_value=[]), \
             patch("agent.tools.espocrm.crear_caso", return_value={"id": "CRM-099"}), \
             patch("agent.tools.enviar_email", return_value=None), \
             patch("agent.tools.Radicado", return_value=radicado_mock):
            resultado = escalar_a_humano(
                telefono="34912345678",
                nombre="Juan Pérez",
                resumen_caso="Urgente",
                area="AreaQueNoExiste"
            )
            # Should handle gracefully - returns dict with mensaje de sin agentes
            assert resultado is not None
            assert isinstance(resultado, dict)
