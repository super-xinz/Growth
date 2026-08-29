import hashlib
import json
import logging
import re
import secrets
import time
from typing import Any

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from .config import Settings

logger = logging.getLogger(__name__)

INSTALLATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,128}$")


def managed_gateway_ready(settings: Settings) -> bool:
    return bool(
        settings.managed_llm_gateway_enabled
        and settings.managed_llm_gateway_token
        and settings.llm_provider == "openai"
        and settings.llm_api_key
        and settings.llm_strong_model
    )


def _bearer_token(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "托管模型凭证缺失")
    return token


def _installation_id(request: Request) -> str:
    value = request.headers.get("x-growthagent-installation", "").strip()
    if not INSTALLATION_ID_PATTERN.fullmatch(value):
        raise HTTPException(401, "安装标识无效，请更新 GrowthAgent 启动器")
    return value


def _validated_payload(raw_body: bytes, settings: Settings) -> dict[str, Any]:
    if len(raw_body) > settings.managed_llm_max_input_chars * 4:
        raise HTTPException(413, "模型请求过大")
    try:
        body = json.loads(raw_body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HTTPException(400, "模型请求不是有效 JSON") from error
    if not isinstance(body, dict):
        raise HTTPException(400, "模型请求格式无效")
    if body.get("stream"):
        raise HTTPException(400, "托管模型暂不支持流式响应")

    messages = body.get("messages")
    if not isinstance(messages, list) or not 1 <= len(messages) <= 24:
        raise HTTPException(400, "模型消息数量无效")
    clean_messages: list[dict[str, str]] = []
    input_chars = 0
    for message in messages:
        if not isinstance(message, dict):
            raise HTTPException(400, "模型消息格式无效")
        role = message.get("role")
        content = message.get("content")
        if role not in {"system", "user", "assistant"} or not isinstance(content, str):
            raise HTTPException(400, "模型消息角色或内容无效")
        input_chars += len(content)
        clean_messages.append({"role": role, "content": content})
    if input_chars > settings.managed_llm_max_input_chars:
        raise HTTPException(413, "模型输入内容过长")

    requested_tokens = body.get("max_tokens", settings.managed_llm_max_output_tokens)
    if not isinstance(requested_tokens, int) or requested_tokens < 1:
        raise HTTPException(400, "max_tokens 无效")
    payload: dict[str, Any] = {
        "model": settings.llm_strong_model,
        "messages": clean_messages,
        "max_tokens": min(requested_tokens, settings.managed_llm_max_output_tokens),
    }
    temperature = body.get("temperature")
    if isinstance(temperature, (int, float)) and 0 <= temperature <= 2:
        payload["temperature"] = temperature
    response_format = body.get("response_format")
    if response_format == {"type": "json_object"}:
        payload["response_format"] = response_format
    thinking = body.get("thinking")
    if isinstance(thinking, dict) and thinking.get("type") in {"enabled", "disabled"}:
        payload["thinking"] = {"type": thinking["type"]}
    if isinstance(body.get("enable_thinking"), bool):
        payload["enable_thinking"] = body["enable_thinking"]
    return payload


async def _increment_limit(redis: Redis, key: str, limit: int, ttl_seconds: int) -> None:
    pipeline = redis.pipeline(transaction=True)
    pipeline.incr(key)
    pipeline.expire(key, ttl_seconds)
    count, _ = await pipeline.execute()
    if int(count) > limit:
        raise HTTPException(429, "托管模型额度已达上限，请稍后再试")


async def _enforce_limits(settings: Settings, installation_id: str) -> None:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    digest = hashlib.sha256(installation_id.encode("utf-8")).hexdigest()[:32]
    minute_bucket = int(time.time() // 60)
    day_bucket = int(time.time() // 86400)
    try:
        await _increment_limit(
            redis,
            f"growthagent:managed-llm:install:{digest}:minute:{minute_bucket}",
            settings.managed_llm_requests_per_minute,
            120,
        )
        await _increment_limit(
            redis,
            f"growthagent:managed-llm:install:{digest}:day:{day_bucket}",
            settings.managed_llm_requests_per_day,
            172800,
        )
        await _increment_limit(
            redis,
            f"growthagent:managed-llm:global:day:{day_bucket}",
            settings.managed_llm_global_requests_per_day,
            172800,
        )
    except HTTPException:
        raise
    except Exception as error:
        logger.warning("Managed LLM rate limiter unavailable: %s", type(error).__name__)
        raise HTTPException(503, "托管模型限流服务暂不可用") from error
    finally:
        await redis.aclose()


async def forward_managed_chat(request: Request, settings: Settings) -> JSONResponse:
    if not managed_gateway_ready(settings):
        raise HTTPException(503, "托管模型服务尚未完成配置")
    token = _bearer_token(request)
    if not secrets.compare_digest(token, settings.managed_llm_gateway_token):
        raise HTTPException(401, "托管模型凭证无效")
    installation_id = _installation_id(request)
    payload = _validated_payload(await request.body(), settings)
    await _enforce_limits(settings, installation_id)

    upstream_url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            response = await client.post(
                upstream_url,
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
    except (httpx.TimeoutException, httpx.NetworkError) as error:
        raise HTTPException(502, "上游模型服务暂时不可用") from error
    try:
        result = response.json()
    except json.JSONDecodeError as error:
        raise HTTPException(502, "上游模型返回格式无效") from error
    if not isinstance(result, dict):
        raise HTTPException(502, "上游模型返回格式无效")
    return JSONResponse(result, status_code=response.status_code, headers={"Cache-Control": "no-store"})
