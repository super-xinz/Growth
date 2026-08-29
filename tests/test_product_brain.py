from types import SimpleNamespace

import pytest
from app.schemas import ProductBrainData
from app.services import _ground_brain_claims, _normalize_brain_output
from pydantic import ValidationError


def test_provider_claim_aliases_are_normalized():
    raw = {
        "claims": [
            {
                "claim": "A sufficiently detailed factual capability.",
                "source_id": "source-1",
                "quote": "Exact evidence quote",
                "confidence": 0.9,
            }
        ]
    }
    normalized = _normalize_brain_output(raw)
    assert "claims" not in normalized
    assert normalized["supported_claims"][0]["source_quote"] == "Exact evidence quote"


def test_incomplete_product_brain_is_rejected():
    with pytest.raises(ValidationError):
        ProductBrainData.model_validate({"product_name": "Degla", "claims": []})


def test_unverifiable_claims_are_replaced_with_exact_source_evidence():
    source = SimpleNamespace(
        id="source-1",
        content="GrowthAgent finds relevant public discussions and preserves source evidence.",
    )
    grounded = _ground_brain_claims(
        {
            "supported_claims": [
                {
                    "claim": "An invented capability that is not supported.",
                    "source_id": "source-1",
                    "source_quote": "This quote never appeared in the source.",
                    "confidence": 0.99,
                }
            ]
        },
        [source],
    )

    exact_excerpt = source.content.rstrip(".")
    assert grounded["supported_claims"] == [
        {
            "claim": exact_excerpt,
            "source_id": source.id,
            "source_quote": exact_excerpt,
            "confidence": 0.6,
        }
    ]
