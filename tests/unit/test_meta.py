import pytest
from unittest.mock import patch, AsyncMock
from agent.providers.meta import ProveedorMeta

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("META_ACCESS_TOKEN", "dummy_token")
    monkeypatch.setenv("META_PHONE_NUMBER_ID", "12345")
    monkeypatch.setenv("META_VERIFY_TOKEN", "dummy_verify")
    monkeypatch.setenv("META_APP_SECRET", "dummy_secret")

def test_parsear_webhook_texto(mock_env):
    provider = ProveedorMeta()
    payload = {
        "entry": [{"changes": [{"value": {
            "contacts": [{"profile": {"name": "Juan"}}],
            "messages": [{"from": "123", "type": "text", "text": {"body": "hola"}}]
        }}]}]
    }
    msg = provider.parsear_webhook(payload)
    assert msg is not None
    assert msg.telefono == "123"
    assert msg.texto == "hola"

def test_parsear_webhook_interactive_button(mock_env):
    provider = ProveedorMeta()
    payload = {
        "entry": [{"changes": [{"value": {
            "contacts": [{"profile": {"name": "Juan"}}],
            "messages": [{"from": "123", "type": "interactive", "interactive": {
                "type": "button_reply",
                "button_reply": {"id": "SI", "title": "Sí, acepto"}
            }}]
        }}]}]
    }
    msg = provider.parsear_webhook(payload)
    assert msg is not None
    assert msg.telefono == "123"
    assert msg.texto == "SI"

@pytest.mark.asyncio
@patch("agent.providers.meta.httpx.AsyncClient.post")
async def test_enviar_mensaje_con_botones(mock_post, mock_env):
    provider = ProveedorMeta()
    mock_post.return_value = AsyncMock(status_code=200, json=lambda: {"msg": "ok"})
    
    botones = [
        {"id": "SI", "title": "Sí"},
        {"id": "NO", "title": "No"}
    ]
    await provider.enviar_mensaje("123", "Aceptas?", botones=botones)
    
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    body = kwargs["json"]
    
    assert body["type"] == "interactive"
    assert body["interactive"]["type"] == "button"
    assert body["interactive"]["body"]["text"] == "Aceptas?"
    assert len(body["interactive"]["action"]["buttons"]) == 2
    assert body["interactive"]["action"]["buttons"][0]["reply"]["id"] == "SI"

@pytest.mark.asyncio
async def test_enviar_mensaje_demasiados_botones(mock_env):
    provider = ProveedorMeta()
    botones = [{"id": str(i), "title": str(i)} for i in range(4)]
    
    with pytest.raises(ValueError):
        await provider.enviar_mensaje("123", "Aceptas?", botones=botones)
