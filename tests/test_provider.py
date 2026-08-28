import pytest
from app.providers import MockLLMProvider


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
