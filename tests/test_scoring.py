def opportunity_score(
    product_fit,
    solution_intent,
    usefulness,
    freshness,
    growth,
    visibility,
    community,
    history,
    risk,
):
    return (
        0.25 * product_fit
        + 0.20 * solution_intent
        + 0.15 * usefulness
        + 0.10 * freshness
        + 0.10 * growth
        + 0.08 * visibility
        + 0.07 * community
        + 0.05 * history
        - risk
    )


def test_high_intent_beats_general_discussion():
    high = opportunity_score(1, 1, 0.8, 0.8, 0.4, 0.5, 0.7, 0, 0)
    low = opportunity_score(0.1, 0, 0.4, 0.8, 0.7, 0.5, 0.7, 0, 0)
    assert high > low
    assert 0 <= high <= 1


def test_risk_penalty_can_force_below_zero_for_policy_clamp():
    assert opportunity_score(0, 0, 0, 0, 0, 0, 0, 0, 0.5) < 0
