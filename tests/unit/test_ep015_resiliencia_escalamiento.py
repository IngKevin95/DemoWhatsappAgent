"""Tests EP-015: manejo generalizado de fallos de Google + notificaciones WhatsApp
a lideres (infra y comercial por area). Trazabilidad: HU-057, HU-058, HU-059."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from agent.tools import (
    agendar_cita,
    consultar_disponibilidad_agenda,
    escalar_a_humano,
    guardar_datos_contacto,
    _manejar_fallo_google,
    _franjas_bd,
    _validar_correo,
    _CITAS_DB,
)


class _RefreshError(Exception):
    """Standin para google.auth.exceptions.RefreshError sin depender del paquete real."""


def _param_session(valores: dict):
    """Mock de SyncSession cuyo query(Parametro).filter(...).first() devuelve un
    objeto con .valor segun la clave consultada en el filtro."""
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)

    def query_side_effect(model):
        q = MagicMock()

        def filter_side_effect(*args, **kwargs):
            # args[0] es la expresión Parametro.clave == "x"; extraemos el rhs
            clave = None
            for a in args:
                rhs = getattr(a, "right", None)
                if rhs is not None:
                    clave = getattr(rhs, "value", None)
            fq = MagicMock()
            valor = valores.get(clave)
            fq.first.return_value = MagicMock(valor=valor) if valor is not None else None
            return fq

        q.filter.side_effect = filter_side_effect
        return q

    session.query.side_effect = query_side_effect
    return session


class TestManejoGeneralizadoFallosGoogle:
    """HU-057: fallo de Google no bloquea; se degrada a la franja de BD y se alerta a infra."""

    def test_refresh_error_en_disponibilidad_degrada_a_franja_bd(self, caplog):
        """HU-057 Scenario 1: al no poder consultar el Calendar, la disponibilidad
        cae a la franja horaria de la BD del agente y se alerta a infra (sin error_servicio)."""
        with patch("agent.tools.horarios_libres", side_effect=_RefreshError("invalid_grant")), \
             patch("agent.tools._agentes_por_area", return_value=[MagicMock(email="a@x.com", hora_inicio="09:00", hora_fin="12:00")]), \
             patch("agent.tools.SyncSession", return_value=_param_session({})), \
             patch("agent.tools._alertar_infra_fallo_google") as mock_alertar:
            with caplog.at_level(logging.WARNING):
                resultado = consultar_disponibilidad_agenda("comercial")

        assert mock_alertar.called, "debe alertar a infra del fallo de Calendar"
        assert isinstance(resultado, list)
        assert all(dia.get("estado") != "error_servicio" for dia in resultado)
        # franja BD 09:00-12:00 -> 09:00,10:00,11:00
        assert resultado[0]["horarios_libres"] == _franjas_bd("09:00", "12:00")

    def test_agendar_con_calendar_caido_agenda_con_franja_bd(self):
        """HU-057 Scenario 2: si no se puede consultar el Calendar, se agenda igual
        validando contra la franja de BD; se alerta a infra pero no se bloquea al cliente."""
        _CITAS_DB.clear()
        persona = MagicMock(email="a@x.com", hora_inicio="09:00", hora_fin="18:00", nombre="Agente 1")
        session = _param_session({})
        session.get = MagicMock(return_value=None)  # sin contacto -> sin correo cliente
        with patch("agent.tools._agentes_por_area", return_value=[persona]), \
             patch("agent.tools.SyncSession", return_value=session), \
             patch("agent.tools.horarios_libres", side_effect=Exception("permission denied")), \
             patch("agent.tools.crear_evento_calendar", return_value={"htmlLink": "http://cal/x"}), \
             patch("agent.tools.espocrm"), \
             patch("agent.tools._alertar_infra_fallo_google") as mock_alertar:
            resultado = agendar_cita(
                nombre="Juan", telefono="3000000000", motivo="Consultoria",
                fecha="2026-08-01", hora="10:00", area="comercial",
            )

        assert mock_alertar.called
        assert "cita_id" in resultado, "debe agendar con la franja de BD, no devolver error_servicio"
        assert resultado.get("estado") != "error_servicio"
        _CITAS_DB.clear()

    def test_agendar_con_creacion_evento_caida_registra_cita_degradada(self):
        """HU-057 Scenario 3: si crear el evento en Calendar falla (404), la cita queda
        registrada igual con marca de degradado; se alerta a infra, no se bloquea."""
        _CITAS_DB.clear()
        persona = MagicMock(email="a@x.com", hora_inicio="09:00", hora_fin="18:00", nombre="Agente 1")
        session = _param_session({})
        session.get = MagicMock(return_value=None)
        with patch("agent.tools._agentes_por_area", return_value=[persona]), \
             patch("agent.tools.SyncSession", return_value=session), \
             patch("agent.tools.horarios_libres", return_value=["10:00"]), \
             patch("agent.tools.crear_evento_calendar", side_effect=Exception("HttpError 404 Not Found")), \
             patch("agent.tools.espocrm"), \
             patch("agent.tools._alertar_infra_fallo_google") as mock_alertar:
            resultado = agendar_cita(
                nombre="Juan", telefono="3000000000", motivo="Consultoria",
                fecha="2026-08-01", hora="10:00", area="comercial",
            )

        assert mock_alertar.called
        assert "cita_id" in resultado
        assert resultado.get("calendar_degradado") is True
        assert resultado.get("estado") != "error_servicio"
        _CITAS_DB.clear()

    def test_happy_path_sin_fallos_no_alerta(self):
        """HU-057 Scenario 4."""
        with patch("agent.tools.horarios_libres", return_value=["09:00", "10:00"]), \
             patch("agent.tools._agentes_por_area", return_value=[MagicMock(email="a@x.com", hora_inicio="09:00", hora_fin="18:00")]), \
             patch("agent.tools.SyncSession", return_value=_param_session({})), \
             patch("agent.tools._alertar_infra_fallo_google") as mock_alertar:
            resultado = consultar_disponibilidad_agenda("comercial")

        assert not mock_alertar.called
        assert isinstance(resultado, list)
        assert all("estado" not in dia for dia in resultado)


class TestValidacionYCorreoInvitado:
    """Validación de formato de correo del cliente + su uso como invitado en la cita."""

    @pytest.mark.parametrize("correo,valido", [
        ("juan@empresa.com", True),
        ("j.perez+demo@sub.dominio.co", True),
        ("juan(arroba)empresa.com", False),
        ("juan@empresa", False),
        ("@empresa.com", False),
        ("juan @empresa.com", False),
        ("", False),
        (None, False),
    ])
    def test_validar_correo_formato(self, correo, valido):
        assert _validar_correo(correo) is valido

    def test_correo_invalido_no_se_guarda_y_pide_correccion(self):
        with patch("agent.tools.SyncSession", return_value=_param_session({})), \
             patch("agent.tools._upsert_contacto") as mock_up, \
             patch("agent.tools._upsert_cliente"):
            resultado = guardar_datos_contacto(
                telefono="3000000000", nombre="Juan", correo="juan(arroba)empresa.com",
            )
        assert resultado["estado"] == "correo_invalido"
        # no se asignó el correo mal formado al contacto
        assert not mock_up.return_value.correo or mock_up.return_value.correo != "juan(arroba)empresa.com"

    def test_correo_valido_se_guarda(self):
        contacto = MagicMock()
        with patch("agent.tools.SyncSession", return_value=_param_session({})), \
             patch("agent.tools._upsert_contacto", return_value=contacto), \
             patch("agent.tools._upsert_cliente"):
            resultado = guardar_datos_contacto(
                telefono="3000000000", nombre="Juan", correo="juan@empresa.com",
            )
        assert resultado["estado"] == "guardado"
        assert contacto.correo == "juan@empresa.com"

    def test_correo_valido_del_cliente_se_pasa_como_invitado(self):
        """El correo válido del cliente llega a crear_evento_calendar como invitado."""
        _CITAS_DB.clear()
        persona = MagicMock(email="a@x.com", hora_inicio="09:00", hora_fin="18:00", nombre="Agente 1")
        session = _param_session({})
        session.get = MagicMock(return_value=MagicMock(correo="cliente@valido.com"))
        with patch("agent.tools._agentes_por_area", return_value=[persona]), \
             patch("agent.tools.SyncSession", return_value=session), \
             patch("agent.tools.horarios_libres", return_value=["10:00"]), \
             patch("agent.tools.crear_evento_calendar", return_value={"htmlLink": "http://cal/x"}) as mock_evt, \
             patch("agent.tools.enviar_email"), \
             patch("agent.tools.espocrm"):
            agendar_cita(
                nombre="Juan", telefono="3000000000", motivo="Consultoria",
                fecha="2026-08-01", hora="10:00", area="comercial",
            )
        # crear_evento_calendar recibe la lista de invitados (agente + cliente)
        assert mock_evt.called
        invitados = mock_evt.call_args.kwargs["correos_invitados"]
        assert "cliente@valido.com" in invitados
        assert "a@x.com" in invitados, "el agente (dueño del calendario) también queda invitado"
        _CITAS_DB.clear()

    def test_correo_invalido_del_cliente_no_se_pasa_como_invitado(self):
        _CITAS_DB.clear()
        persona = MagicMock(email="a@x.com", hora_inicio="09:00", hora_fin="18:00", nombre="Agente 1")
        session = _param_session({})
        session.get = MagicMock(return_value=MagicMock(correo="cliente-invalido"))
        with patch("agent.tools._agentes_por_area", return_value=[persona]), \
             patch("agent.tools.SyncSession", return_value=session), \
             patch("agent.tools.horarios_libres", return_value=["10:00"]), \
             patch("agent.tools.crear_evento_calendar", return_value={"htmlLink": "http://cal/x"}) as mock_evt, \
             patch("agent.tools.enviar_email"), \
             patch("agent.tools.espocrm"):
            agendar_cita(
                nombre="Juan", telefono="3000000000", motivo="Consultoria",
                fecha="2026-08-01", hora="10:00", area="comercial",
            )
        assert mock_evt.called
        invitados = mock_evt.call_args.kwargs["correos_invitados"]
        assert "cliente-invalido" not in invitados
        assert invitados == ["a@x.com"], "solo el agente; el correo inválido del cliente se descarta"
        _CITAS_DB.clear()

    def test_multiples_correos_cliente_todos_quedan_invitados(self):
        """HU-061: varios correos del cliente (coma) -> todos los válidos como invitados."""
        _CITAS_DB.clear()
        persona = MagicMock(email="a@x.com", hora_inicio="09:00", hora_fin="18:00", nombre="Agente 1")
        session = _param_session({})
        session.get = MagicMock(return_value=MagicMock(correo="uno@c.com, dos@c.com , malo"))
        with patch("agent.tools._agentes_por_area", return_value=[persona]), \
             patch("agent.tools.SyncSession", return_value=session), \
             patch("agent.tools.horarios_libres", return_value=["10:00"]), \
             patch("agent.tools.crear_evento_calendar", return_value={"htmlLink": "http://cal/x"}) as mock_evt, \
             patch("agent.tools.enviar_email") as mock_mail, \
             patch("agent.tools.espocrm"):
            resultado = agendar_cita(
                nombre="Juan", telefono="3000000000", motivo="Consultoria",
                fecha="2026-08-01", hora="10:00", area="comercial",
            )
        invitados = mock_evt.call_args.kwargs["correos_invitados"]
        assert invitados == ["a@x.com", "uno@c.com", "dos@c.com"], "agente + los 2 correos válidos, 'malo' descartado"
        assert resultado["invitados"] == invitados
        # confirmación enviada a cada correo válido del cliente (no al 'malo')
        destinatarios = {c.args[0] for c in mock_mail.call_args_list}
        assert destinatarios == {"uno@c.com", "dos@c.com"}
        _CITAS_DB.clear()

    def test_guardar_multiples_correos_separa_validos_de_invalidos(self):
        """HU-061: guardar_datos_contacto persiste los válidos y reporta los inválidos."""
        contacto = MagicMock()
        with patch("agent.tools.SyncSession", return_value=_param_session({})), \
             patch("agent.tools._upsert_contacto", return_value=contacto), \
             patch("agent.tools._upsert_cliente"):
            resultado = guardar_datos_contacto(
                telefono="3000000000", nombre="Juan", correo="ok@c.com, malo, otro@c.com",
            )
        assert resultado["estado"] == "correo_invalido"
        assert resultado["guardados"] == ["ok@c.com", "otro@c.com"]
        assert resultado["invalidos"] == ["malo"]
        assert contacto.correo == "ok@c.com,otro@c.com"


class TestNotificacionLiderInfra:
    """HU-058: WhatsApp al lider de infraestructura ante fallo tecnico."""

    def test_whatsapp_a_infra_cuando_parametro_configurado(self):
        """HU-058 Scenario 1."""
        session = _param_session({"whatsapp_lider_infra": "3001234567"})
        with patch("agent.tools.SyncSession", return_value=session), \
             patch("agent.tools.enviar_email"), \
             patch("agent.tools.escalar_a_humano"), \
             patch("agent.tools._enviar_whatsapp_directo") as mock_wa:
            _manejar_fallo_google(Exception("boom"), "comercial", "3000000000", "Juan", resumen="fallo")

        assert mock_wa.called
        llamada = mock_wa.call_args
        assert llamada.args[0] == "3001234567" or llamada.kwargs.get("telefono") == "3001234567"

    def test_sin_parametro_no_envia_y_loguea(self, caplog):
        """HU-058 Scenario 2."""
        session = _param_session({})
        with patch("agent.tools.SyncSession", return_value=session), \
             patch("agent.tools.enviar_email"), \
             patch("agent.tools.escalar_a_humano"), \
             patch("agent.tools._enviar_whatsapp_directo") as mock_wa:
            with caplog.at_level(logging.INFO):
                _manejar_fallo_google(Exception("boom"), "comercial", "3000000000", "Juan", resumen="fallo")

        assert not mock_wa.called

    def test_fallo_en_envio_no_interrumpe_flujo(self):
        """HU-058 Scenario 3."""
        session = _param_session({"whatsapp_lider_infra": "3001234567"})
        with patch("agent.tools.SyncSession", return_value=session), \
             patch("agent.tools.enviar_email"), \
             patch("agent.tools.escalar_a_humano") as mock_escalar, \
             patch("agent.tools._enviar_whatsapp_directo", side_effect=Exception("red caida")):
            # no debe propagar la excepción
            _manejar_fallo_google(Exception("boom"), "comercial", "3000000000", "Juan", resumen="fallo")

        assert mock_escalar.called


class TestNotificacionLiderComercialEnCola:
    """HU-059: WhatsApp al lider comercial de area cuando un caso entra en cola."""

    def _session_para_cola(self, valores_parametro: dict):
        session = _param_session(valores_parametro)
        area_row = MagicMock(id=1)
        radicado_mock = MagicMock(id=99, email_enviado=True, crm_case_id="CRM-1")

        # override para exponer también filter().first() de área y las llamadas de conteo
        orig_query_side_effect = session.query.side_effect

        def query_side_effect(model):
            name = getattr(model, "__name__", "")
            if name == "Parametro":
                return orig_query_side_effect(model)
            q = MagicMock()
            q.filter.return_value.first.return_value = area_row
            q.filter.return_value.order_by.return_value.first.return_value = None
            q.join.return_value.filter.return_value.count.return_value = 0
            q.get.return_value = None
            return q

        session.query.side_effect = query_side_effect
        return session, area_row, radicado_mock

    def test_cola_con_lider_configurado_envia_whatsapp(self):
        """HU-059 Scenario 1."""
        session, area_row, radicado_mock = self._session_para_cola({"whatsapp_lider_comercial": "3009999999"})
        with patch("agent.tools.SyncSession", return_value=session), \
             patch("agent.tools._upsert_contacto", return_value=MagicMock()), \
             patch("agent.tools._get_area", return_value=area_row), \
             patch("agent.tools._agentes_por_area", return_value=[MagicMock(id=1, telefono="3001111111", nombre="Agente 1")]), \
             patch("agent.tools._ocupados", return_value={1}), \
             patch("agent.tools.espocrm.crear_caso", return_value={"id": "CRM-1"}), \
             patch("agent.tools.enviar_email", return_value=None), \
             patch("agent.tools.Radicado", return_value=radicado_mock), \
             patch("agent.tools._enviar_whatsapp_directo") as mock_wa:
            resultado = escalar_a_humano("3000000000", "Juan", "resumen", "comercial")

        assert resultado["estado"] == "en_cola"
        assert mock_wa.called
        args, kwargs = mock_wa.call_args
        destino = args[0] if args else kwargs.get("telefono")
        assert destino == "3009999999"

    def test_asignacion_directa_no_notifica_lider(self):
        """HU-059 Scenario 2."""
        session, area_row, radicado_mock = self._session_para_cola({"whatsapp_lider_comercial": "3009999999"})
        with patch("agent.tools.SyncSession", return_value=session), \
             patch("agent.tools._upsert_contacto", return_value=MagicMock()), \
             patch("agent.tools._get_area", return_value=area_row), \
             patch("agent.tools._agentes_por_area", return_value=[MagicMock(id=1, telefono=None, nombre="Agente 1")]), \
             patch("agent.tools._ocupados", return_value=set()), \
             patch("agent.tools.espocrm.crear_caso", return_value={"id": "CRM-1"}), \
             patch("agent.tools.enviar_email", return_value=None), \
             patch("agent.tools.Radicado", return_value=radicado_mock), \
             patch("agent.tools._enviar_whatsapp_directo") as mock_wa:
            resultado = escalar_a_humano("3000000000", "Juan", "resumen", "comercial")

        assert resultado["estado"] == "escalado"
        assert not mock_wa.called

    def test_sin_parametro_area_no_envia(self):
        """HU-059 Scenario 3."""
        session, area_row, radicado_mock = self._session_para_cola({})
        with patch("agent.tools.SyncSession", return_value=session), \
             patch("agent.tools._upsert_contacto", return_value=MagicMock()), \
             patch("agent.tools._get_area", return_value=area_row), \
             patch("agent.tools._agentes_por_area", return_value=[MagicMock(id=1, telefono="3001111111", nombre="Agente 1")]), \
             patch("agent.tools._ocupados", return_value={1}), \
             patch("agent.tools.espocrm.crear_caso", return_value={"id": "CRM-1"}), \
             patch("agent.tools.enviar_email", return_value=None), \
             patch("agent.tools.Radicado", return_value=radicado_mock), \
             patch("agent.tools._enviar_whatsapp_directo") as mock_wa:
            resultado = escalar_a_humano("3000000000", "Juan", "resumen", "comercial")

        assert resultado["estado"] == "en_cola"
        assert not mock_wa.called

    def test_fallo_envio_lider_no_afecta_respuesta_cliente(self):
        """HU-059 Scenario 4."""
        session, area_row, radicado_mock = self._session_para_cola({"whatsapp_lider_comercial": "3009999999"})
        with patch("agent.tools.SyncSession", return_value=session), \
             patch("agent.tools._upsert_contacto", return_value=MagicMock()), \
             patch("agent.tools._get_area", return_value=area_row), \
             patch("agent.tools._agentes_por_area", return_value=[MagicMock(id=1, telefono="3001111111", nombre="Agente 1")]), \
             patch("agent.tools._ocupados", return_value={1}), \
             patch("agent.tools.espocrm.crear_caso", return_value={"id": "CRM-1"}), \
             patch("agent.tools.enviar_email", return_value=None), \
             patch("agent.tools.Radicado", return_value=radicado_mock), \
             patch("agent.tools._enviar_whatsapp_directo", side_effect=Exception("fallo meta")):
            resultado = escalar_a_humano("3000000000", "Juan", "resumen", "comercial")

        assert resultado["estado"] == "en_cola"
        assert "posicion" in resultado
