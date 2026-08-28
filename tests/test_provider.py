import pytest
from app.config import Settings
from app.providers import MockLLMProvider, OpenAICompatibleProvider


@pytest.mark.asyncio
async def test_mock_brain_claims_keep_source_evidence():
    provider = MockLLMProvider()
    brain = await provider.generate_structured(
        "product_brain_v1",
        {
            "product_name": "Pilot",
            "sources": [
                {
                    "id": "s1",
                    "content": "Pilot monitors explicit product recommendations and preserves audit evidence.",
                }
            ],
        },
        {},
    )
    assert brain["product_name"] == "Pilot"
    assert all(c["source_id"] == "s1" and c["source_quote"] for c in brain["supported_claims"])
    assert "query_graph" in brain


def test_deepseek_provider_sends_explicit_thinking_mode():
    provider = OpenAICompatibleProvider(
        Settings(
            llm_provider="openai",
            llm_api_key="test-key",
            llm_base_url="https://api.deepseek.com",
            llm_strong_model="deepseek-v4-flash",
            llm_enable_thinking=False,
        )
    )

    assert provider.extra_body == {"thinking": {"type": "disabled"}}
