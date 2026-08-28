from app.services import classify_followup_intent


def test_followup_link_request_is_detected():
    assert classify_followup_intent("Can you send me the link?") == "ASK_LINK"


def test_negative_reaction_stops_conversation():
    assert classify_followup_intent("Stop spamming your product.") == "NEGATIVE_REACTION"


def test_moderator_warning_has_priority():
    assert (
        classify_followup_intent("Moderator note: this was removed for rule violation.")
        == "MOD_WARNING"
    )
