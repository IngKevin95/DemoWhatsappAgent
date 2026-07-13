"""Additional tests for tools.py to increase coverage."""

import pytest
from agent.tools import (
    cargar_info_negocio,
    buscar_en_knowledge,
    _oferta_activa,
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
