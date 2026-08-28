import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings, get_settings
from .models import AppSetting

LLM_SETTINGS_KEY = "llm"
LLM_FIELDS = {
    "llm_provider",
    "llm_api_key",
    "llm_base_url",
    "llm_strong_model",
    "llm_enable_thinking",
}


def _fernet(settings: Settings | None = None) -> Fernet:
    secret = (settings or get_settings()).encryption_key
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_settings(payload: dict[str, Any], settings: Settings | None = None) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return _fernet(settings).encrypt(encoded).decode("ascii")


def decrypt_settings(value: str, settings: Settings | None = None) -> dict[str, Any]:
    try:
        decoded = _fernet(settings).decrypt(value.encode("ascii"))
        payload = json.loads(decoded)
    except (InvalidToken, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("保存的模型配置无法解密，请检查 ENCRYPTION_KEY") from error
    if not isinstance(payload, dict):
        raise ValueError("保存的模型配置格式无效")
    return {key: item for key, item in payload.items() if key in LLM_FIELDS}


async def llm_settings_payload(db: AsyncSession) -> dict[str, Any]:
    row = await db.get(AppSetting, LLM_SETTINGS_KEY)
    return decrypt_settings(row.value_encrypted) if row else {}


async def effective_settings(db: AsyncSession) -> Settings:
    payload = await llm_settings_payload(db)
    return get_settings().model_copy(update=payload)


async def save_llm_settings(db: AsyncSession, payload: dict[str, Any]) -> None:
    clean = {key: item for key, item in payload.items() if key in LLM_FIELDS}
    row = await db.get(AppSetting, LLM_SETTINGS_KEY)
    encrypted = encrypt_settings(clean)
    if row:
        row.value_encrypted = encrypted
    else:
        db.add(AppSetting(key=LLM_SETTINGS_KEY, value_encrypted=encrypted))
    await db.commit()
