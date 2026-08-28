import pytest
from pydantic import ValidationError

from app.schemas import ProductBrainData
from app.services import _normalize_brain_output


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
