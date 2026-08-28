import pytest
from sqlalchemy import select

from app.config import Settings
from app.models import AppSetting
from app.runtime_settings import decrypt_settings, encrypt_settings

pytest_plugins = ["test_api_workflow"]


def test_settings_encryption_roundtrip_and_wrong_key_rejection():
    first = Settings(encryption_key="first-test-key")
    encrypted = encrypt_settings({"llm_api_key": "sk-super-secret", "ignored": "no"}, first)

    assert "sk-super-secret" not in encrypted
    assert decrypt_settings(encrypted, first) == {"llm_api_key": "sk-super-secret"}
    with pytest.raises(ValueError, match="ENCRYPTION_KEY"):
        decrypt_settings(encrypted, Settings(encryption_key="different-test-key"))


@pytest.mark.asyncio
async def test_llm_settings_api_never_returns_plaintext_key(api_client):
    client, session_factory = api_client
    secret = "test-provider-key-1234"

    saved = await client.put(
        "/v1/settings/llm",
        json={
            "provider": "openai",
            "api_key": secret,
            "base_url": "https://api.openai.com/v1",
            "model": "test-model",
            "enable_thinking": False,
        },
    )
    assert saved.status_code == 200
    assert saved.json()["api_key_hint"] == "••••1234"
    assert secret not in saved.text

    fetched = await client.get("/v1/settings/llm")
    assert fetched.status_code == 200
    assert secret not in fetched.text

    async with session_factory() as db:
        row = await db.scalar(select(AppSetting).where(AppSetting.key == "llm"))
        assert row is not None
        assert secret not in row.value_encrypted

    preserved = await client.put(
        "/v1/settings/llm",
        json={
            "provider": "openai",
            "api_key": None,
            "base_url": "https://api.openai.com/v1",
            "model": "test-model",
        },
    )
    assert preserved.json()["api_key_hint"] == "••••1234"
