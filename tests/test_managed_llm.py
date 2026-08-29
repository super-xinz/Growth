import json

import httpx
import pytest
from app.config import Settings
from app.managed_llm import (
    _validated_payload,
    forward_managed_chat,
    managed_gateway_ready,
)
from fastapi import HTTPException
from starlette.requests import Request


def gateway_settings(**updates) -> Settings:
    values = {
        "llm_provider": "openai",
        "llm_api_key": "upstream-provider-key",
        "llm_base_url": "https://api.deepseek.example",
        "llm_strong_model": "deepseek-v4-flash",
        "managed_llm_gateway_enabled": True,
        "managed_llm_gateway_token": "release-gateway-token",
    }
    values.update(updates)
    return Settings(**values)


def request_for(body: dict, *, token: str = "release-gateway-token", install_id: str = "ga_test_install_1234") -> Request:
    raw_body = json.dumps(body).encode("utf-8")
    delivered = False

    async def receive():
        nonlocal delivered
        if delivered:
            return {"type": "http.request", "body": b"", "more_body": False}
        delivered = True
        return {"type": "http.request", "body": raw_body, "more_body": False}

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/v1/managed-llm/chat/completions",
            "headers": [
                (b"authorization", f"Bearer {token}".encode("ascii")),
                (b"x-growthagent-installation", install_id.encode("ascii")),
            ],
        },
        receive,
    )


def test_managed_gateway_requires_complete_server_side_configuration():
    assert managed_gateway_ready(gateway_settings()) is True
    assert managed_gateway_ready(gateway_settings(llm_api_key="")) is False
    assert managed_gateway_ready(gateway_settings(managed_llm_gateway_token="")) is False


def test_managed_gateway_forces_model_and_caps_output():
    payload = _validated_payload(
        json.dumps(
            {
                "model": "attacker-selected-model",
                "messages": [{"role": "user", "content": "只回复 OK"}],
                "max_tokens": 999999,
                "stream": False,
            }
        ).encode(),
        gateway_settings(managed_llm_max_output_tokens=120),
    )
    assert payload["model"] == "deepseek-v4-flash"
    assert payload["max_tokens"] == 120


@pytest.mark.asyncio
async def test_managed_gateway_forwards_without_exposing_upstream_key(monkeypatch):
    captured = {}

    async def allow_limits(_settings, installation_id):
        assert installation_id == "ga_test_install_1234"

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, *, headers, json):
            captured.update(url=url, headers=headers, payload=json)
            return httpx.Response(
                200,
                json={
                    "model": "deepseek-v4-flash",
                    "choices": [{"message": {"role": "assistant", "content": "OK"}}],
                },
            )

    monkeypatch.setattr("app.managed_llm._enforce_limits", allow_limits)
    monkeypatch.setattr("app.managed_llm.httpx.AsyncClient", FakeClient)
    response = await forward_managed_chat(
        request_for(
            {
                "model": "deepseek-v4-flash",
                "messages": [{"role": "user", "content": "只回复 OK"}],
                "max_tokens": 32,
            }
        ),
        gateway_settings(),
    )

    assert response.status_code == 200
    assert captured["url"] == "https://api.deepseek.example/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer upstream-provider-key"
    assert b"upstream-provider-key" not in response.body
    assert json.loads(response.body)["choices"][0]["message"]["content"] == "OK"


@pytest.mark.asyncio
async def test_managed_gateway_rejects_invalid_installation_id():
    with pytest.raises(HTTPException) as raised:
        await forward_managed_chat(
            request_for(
                {"messages": [{"role": "user", "content": "OK"}]},
                install_id="invalid",
            ),
            gateway_settings(),
        )
    assert getattr(raised.value, "status_code", None) == 401
