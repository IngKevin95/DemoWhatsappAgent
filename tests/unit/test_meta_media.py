import pytest
from unittest.mock import patch, AsyncMock
from agent.providers.meta import ProveedorMeta

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "dummy_token")
    monkeypatch.setenv("META_PHONE_NUMBER_ID", "12345")
    monkeypatch.setenv("META_VERIFY_TOKEN", "dummy_verify")
    monkeypatch.setenv("META_APP_SECRET", "dummy_secret")

def test_parsear_webhook_documento(mock_env):
    provider = ProveedorMeta()
    payload = {
        "entry": [{"changes": [{"value": {
            "contacts": [{"profile": {"name": "Juan"}}],
            "messages": [{"from": "123", "type": "document", "document": {"id": "doc123", "filename": "test.pdf"}}]
        }}]}]
    }
    msg = provider.parsear_webhook(payload)
    assert msg is not None
    assert msg.telefono == "123"
    assert msg.tipo == "document"
    assert msg.media_id == "doc123"

def test_parsear_webhook_audio(mock_env):
    provider = ProveedorMeta()
    payload = {
        "entry": [{"changes": [{"value": {
            "contacts": [{"profile": {"name": "Juan"}}],
            "messages": [{"from": "123", "type": "audio", "audio": {"id": "audio123"}}]
        }}]}]
    }
    msg = provider.parsear_webhook(payload)
    assert msg is not None
    assert msg.telefono == "123"
    assert msg.tipo == "audio"
    assert msg.media_id == "audio123"

@pytest.mark.asyncio
@patch("agent.providers.meta.httpx.AsyncClient.post")
async def test_enviar_mensaje_template_carrusel(mock_post, mock_env):
    provider = ProveedorMeta()
    mock_post.return_value = AsyncMock(status_code=200, json=lambda: {"msg": "ok"})
    
    template_data = {
        "name": "ofertas_carrusel",
        "language": {"code": "es"},
        "components": [{"type": "body", "parameters": []}]
    }
    
    await provider.enviar_mensaje("123", "", template=template_data)
    
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    body = kwargs["json"]
    
    assert body["type"] == "template"
    assert body["template"]["name"] == "ofertas_carrusel"

@pytest.mark.asyncio
@patch("agent.providers.meta.httpx.AsyncClient.post")
async def test_enviar_mensaje_documento(mock_post, mock_env):
    provider = ProveedorMeta()
    mock_post.return_value = AsyncMock(status_code=200, json=lambda: {"msg": "ok"})
    
    documento_data = {
        "link": "http://example.com/file.pdf",
        "filename": "cotizacion.pdf"
    }
    
    await provider.enviar_mensaje("123", "", documento=documento_data)
    
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    body = kwargs["json"]
    
    assert body["type"] == "document"
    assert body["document"]["link"] == "http://example.com/file.pdf"
    assert body["document"]["filename"] == "cotizacion.pdf"

@pytest.mark.asyncio
@patch("agent.providers.meta.httpx.AsyncClient.get")
async def test_descargar_media(mock_get, mock_env):
    provider = ProveedorMeta()
    # Mock para obtener la URL de la media
    mock_get.side_effect = [
        AsyncMock(status_code=200, json=lambda: {"url": "http://graph.facebook.com/v20.0/media/url"}),
        AsyncMock(status_code=200, content=b"audio_content")
    ]
    
    content = await provider.descargar_media("audio123")
    assert content == b"audio_content"
    assert mock_get.call_count == 2
