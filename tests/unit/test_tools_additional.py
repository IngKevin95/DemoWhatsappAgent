"""Additional tests for tools.py to increase coverage."""

import pytest
from agent.tools import (
    cargar_info_negocio,
    buscar_en_knowledge,
    _oferta_activa,
    consultar_ofertas_activas,
    consultar_parametro,
    consultar_estado_cliente,
    consultar_licencia,
    _agentes_por_area,
    _ocupados,
    _obtener_horario_atencion,
)
from unittest.mock import MagicMock, patch


def test_cargar_info_negocio():
    """cargar_info_negocio loads knowledge files."""
    content = cargar_info_negocio()
    assert isinstance(content, str)


def test_buscar_en_knowledge():
    """buscar_en_knowledge searches knowledge base."""
    result = buscar_en_knowledge("Pro")
    assert isinstance(result, str)


def test_oferta_activa():
    """_oferta_activa finds active offer."""
    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = None
    result = _oferta_activa(mock_session, 1)
    assert result is None or isinstance(result, type(None))


@patch("agent.tools.SyncSession")
def test_consultar_ofertas_activas(mock_sync_session):
    mock_session = MagicMock()
    mock_sync_session.return_value.__enter__.return_value = mock_session
    mock_session.query.return_value.filter.return_value.all.return_value = []
    res = consultar_ofertas_activas()
    assert isinstance(res, list)


@patch("agent.tools.SyncSession")
def test_consultar_parametro(mock_sync_session):
    mock_session = MagicMock()
    mock_sync_session.return_value.__enter__.return_value = mock_session
    mock_session.query.return_value.filter.return_value.first.return_value = None
    res = consultar_parametro("TEST")
    assert isinstance(res, dict)
    assert "error" in res or res.get("valor") is None


@patch("agent.tools.SyncSession")
def test_consultar_estado_cliente(mock_sync_session):
    mock_session = MagicMock()
    mock_sync_session.return_value.__enter__.return_value = mock_session
    mock_session.query.return_value.filter_by.return_value.first.return_value = None
    res = consultar_estado_cliente("123")
    assert isinstance(res, dict)


@patch("agent.tools.SyncSession")
def test_consultar_licencia(mock_sync_session):
    mock_session = MagicMock()
    mock_sync_session.return_value.__enter__.return_value = mock_session
    mock_session.query.return_value.filter.return_value.first.return_value = None
    res = consultar_licencia("123")
    assert isinstance(res, dict)


def test_agentes_por_area():
    mock_session = MagicMock()
    mock_session.query.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = []
    res = _agentes_por_area(mock_session, "comercial")
    assert isinstance(res, list)


def test_ocupados():
    res = _ocupados()
    assert isinstance(res, set)


@patch("agent.tools.SyncSession")
def test_obtener_horario_atencion(mock_sync_session):
    mock_session = MagicMock()
    mock_sync_session.return_value.__enter__.return_value = mock_session
    mock_param = MagicMock()
    mock_param.valor = "Horario Test"
    mock_session.query.return_value.filter.return_value.first.return_value = mock_param
    res = _obtener_horario_atencion()
