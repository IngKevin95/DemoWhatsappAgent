import pytest
from unittest.mock import patch, AsyncMock
from agent.providers.telegram import ProveedorTelegram

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "dummy_token")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "dummy_secret")

def test_validar_webhook_telegram(mock_env):
    provider = ProveedorTelegram()
    assert provider.validar_webhook({}) == "ok"  # Telegram setWebhook returns true internally usually, but we keep signature
    # Actually Telegram verification usually checks secret token in headers
    # We will test `validar_firma` for Telegram since it uses X-Telegram-Bot-Api-Secret-Token
    assert provider.validar_firma(b"body", "dummy_secret") is True
    assert provider.validar_firma(b"body", "wrong_secret") is False

def test_parsear_webhook_texto(mock_env):
    provider = ProveedorTelegram()
    payload = {
        "update_id": 12345,
        "message": {
            "message_id": 1,
            "from": {"id": 111, "first_name": "Juan"},
            "chat": {"id": 111, "type": "private"},
            "date": 1600000000,
            "text": "hola"
        }
    }
    msg = provider.parsear_webhook(payload)
    assert msg is not None
    assert msg.telefono == "111"
    assert msg.texto == "hola"
    assert msg.nombre == "Juan"

@pytest.mark.asyncio
@patch("agent.providers.telegram.httpx.AsyncClient.post")
async def test_enviar_mensaje_texto(mock_post, mock_env):
    provider = ProveedorTelegram()
    mock_post.return_value = AsyncMock(status_code=200, json=lambda: {"ok": True})
    
    await provider.enviar_mensaje("111", "Hola desde Telegram")
    
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    body = kwargs["json"]
    
    assert body["chat_id"] == "111"
    assert body["text"] == "Hola desde Telegram"
