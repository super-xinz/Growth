import json
import re
from abc import ABC, abstractmethod
from collections import Counter
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI, BadRequestError
from .config import Settings
from .prompting import (
    OPPORTUNITY_SCORING_SYSTEM_PROMPT,
    PRODUCT_BRAIN_SYSTEM_PROMPT,
    SEARCH_KEYWORD_SYSTEM_PROMPT,
)


class LLMProviderError(RuntimeError):
    """A safe, actionable provider error that can be shown by the API."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class LLMProvider(ABC):
    @abstractmethod
    async def generate_structured(self, task: str, payload: dict, schema: dict) -> dict: ...
    @abstractmethod
    async def generate_text(self, prompt: str) -> str: ...
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class MockLLMProvider(LLMProvider):
    async def generate_structured(self, task: str, payload: dict, schema: dict) -> dict:
        if task == "select_search_keywords":
            graph = payload.get("query_graph", {})
            terms = (
                graph.get("pain_phrases", [])
                + graph.get("use_cases", [])
                + graph.get("direct_terms", [])
            )
            keywords = []
            for term in terms:
                cleaned = str(term).strip()
                if cleaned and cleaned not in [item["keyword"] for item in keywords]:
                    keywords.append(
                        {"keyword": cleaned, "selection_reason": "来自 Product Brain 的需求信号"}
                    )
            return {"keywords": keywords[: payload.get("count", 3)]}

        if task == "evaluate_opportunity":
            content = payload.get("content_body", "")
            demand_signal = any(mark in content for mark in ("?", "？", "求", "推荐", "有没有", "怎么"))
            return {
                "opportunity_score": 0.85 if demand_signal else 0.55,
                "risk_score": 0.05,
                "reasoning": "Mock opportunity evaluation based on demand markers.",
                "match_signals": ["求助表达"] if demand_signal else [],
            }

        sources = payload.get("sources", [])
        text = " ".join(s.get("content", "") for s in sources)
        words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9-]{3,}", text)]
        common = [
            w
            for w, _ in Counter(words).most_common(12)
            if w not in {"this", "that", "with", "from", "your", "have", "will", "https"}
        ]
        name = payload.get("product_name", "Product")
        claims = []
        for source in sources[:5]:
            sentence = next(
                (
                    x.strip()
                    for x in re.split(r"[.!?]", source.get("content", ""))
                    if len(x.strip()) > 25
                ),
                "",
            )
            if sentence:
                claims.append(
                    {
                        "claim": sentence[:240],
                        "source_id": source["id"],
                        "source_quote": sentence[:300],
                        "confidence": 0.75,
                    }
                )
        return {
            "product_name": name,
            "one_liner": f"{name} helps users with {', '.join(common[:3]) or 'their workflow'}.",
            "category": common[0] if common else "software",
            "target_users": ["teams evaluating this workflow"],
            "jobs_to_be_done": [f"Improve {w}" for w in common[:3]],
            "pain_points": [f"Difficulty with {w}" for w in common[3:6]],
            "use_cases": common[:5],
            "competitors": [],
            "alternatives": ["manual workflow"],
            "recommend_when": [f"Someone explicitly needs {w}" for w in common[:3]],
            "do_not_recommend_when": ["The requested capability is not supported by cited sources"],
            "supported_claims": claims,
            "unsupported_or_uncertain_claims": [],
            "pricing_summary": "Not verified",
            "disclosure_identity": "Relationship to the product has not been verified",
            "query_graph": {
                "direct_terms": common[:5],
                "pain_phrases": [f"looking for {w}" for w in common[:4]],
                "intent_patterns": [
                    "looking for",
                    "any recommendations",
                    "alternative to",
                    "how do I",
                ],
                "competitors": [],
                "use_cases": common[:5],
                "negative_terms": [],
            },
        }

    async def generate_text(self, prompt: str) -> str:
        return "Mock response"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t) % 17) / 17] * 8 for t in texts]


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, settings: Settings):
        if not settings.llm_api_key or not settings.llm_strong_model:
            raise ValueError("LLM_API_KEY and LLM_STRONG_MODEL are required")
        self.client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=settings.llm_timeout_seconds,
            max_retries=0,
        )
        self.model = settings.llm_strong_model
        self.extra_body = (
            {"enable_thinking": settings.llm_enable_thinking}
            if "dashscope" in settings.llm_base_url.lower()
            or self.model.lower().startswith("qwen")
            else None
        )

    async def generate_structured(self, task: str, payload: dict, schema: dict) -> dict:
        system = {
            "evaluate_opportunity": OPPORTUNITY_SCORING_SYSTEM_PROMPT,
            "select_search_keywords": SEARCH_KEYWORD_SYSTEM_PROMPT,
        }.get(task, PRODUCT_BRAIN_SYSTEM_PROMPT)
        messages = [
            {"role": "system", "content": f"{system}\n任务标识：{task}"},
            {
                "role": "user",
                "content": json.dumps(
                    {"input": payload, "required_output_schema": schema}, ensure_ascii=False
                ),
            },
        ]
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                temperature=0.1,
                max_tokens=5000,
                response_format={"type": "json_object"},
                extra_body=self.extra_body,
                messages=messages,
            )
        except BadRequestError as error:
            # Some OpenAI-compatible providers do not implement response_format.
            if "response_format" not in str(error).lower() and "json" not in str(error).lower():
                raise self._provider_error(error) from error
            response = await self._create_without_response_format(messages)
        except (APITimeoutError, APIConnectionError, APIStatusError) as error:
            raise self._provider_error(error) from error
        content = (response.choices[0].message.content or "{}").strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.IGNORECASE)
        try:
            return json.loads(content)
        except json.JSONDecodeError as error:
            raise LLMProviderError("INVALID_JSON", "模型返回格式异常，已保留原产品数据，可稍后重试") from error

    async def _create_without_response_format(self, messages: list[dict]):
        try:
            return await self.client.chat.completions.create(
                model=self.model,
                temperature=0.1,
                max_tokens=5000,
                extra_body=self.extra_body,
                messages=messages,
            )
        except (APITimeoutError, APIConnectionError, APIStatusError) as error:
            raise self._provider_error(error) from error

    @staticmethod
    def _provider_error(error: Exception) -> LLMProviderError:
        if isinstance(error, APITimeoutError):
            return LLMProviderError("TIMEOUT", "模型分析超时，请稍后重试；已保留已抓取的产品资料")
        if isinstance(error, APIConnectionError):
            return LLMProviderError("CONNECTION", "无法连接模型服务，请检查 LLM_BASE_URL 或网络")
        status = getattr(error, "status_code", None)
        if status in {401, 403}:
            return LLMProviderError("AUTH", "模型鉴权失败，请检查 LLM_API_KEY")
        if status == 429:
            return LLMProviderError("RATE_LIMIT", "模型额度或频率受限，请稍后重试")
        if status == 404:
            return LLMProviderError("MODEL_NOT_FOUND", "模型名称不可用，请检查 LLM_STRONG_MODEL")
        return LLMProviderError("PROVIDER", f"模型服务返回异常（HTTP {status or '未知'}）")

    async def generate_text(self, prompt: str) -> str:
        try:
            r = await self.client.chat.completions.create(
                model=self.model,
                temperature=0.35,
                max_tokens=120,
                extra_body=self.extra_body,
                messages=[{"role": "user", "content": prompt}],
            )
        except (APITimeoutError, APIConnectionError, APIStatusError) as error:
            raise self._provider_error(error) from error
        return r.choices[0].message.content or ""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("Configure a dedicated embedding provider before live reranking")


def provider_for(settings: Settings) -> LLMProvider:
    return (
        MockLLMProvider() if settings.llm_provider == "mock" else OpenAICompatibleProvider(settings)
    )
