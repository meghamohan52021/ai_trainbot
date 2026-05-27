from reasoning_engine import (
    decide_intent_with_rules,
    decide_next_ticket_action,
    decide_next_delay_action,
    post_prediction_advice,
)


def test_ticket_intent_routes_to_ticket_flow():
    assert decide_intent_with_rules("ticket") == "ticket_flow"


def test_delay_intent_routes_to_delay_flow():
    assert decide_intent_with_rules("delay") == "delay_flow"


def test_unknown_intent_routes_to_faq_flow():
    assert decide_intent_with_rules("unknown") == "faq_flow"


def test_ticket_complete_when_no_missing_slots():
    assert decide_next_ticket_action([]) == "ticket_complete"


def test_ticket_asks_for_from_station():
    response = decide_next_ticket_action(["from_station"])
    assert "Where are you travelling from" in response


def test_ticket_asks_for_journey_type():
    response = decide_next_ticket_action(["journey_type"])
    assert "single or return" in response


def test_delay_complete_when_no_missing_slots():
    assert decide_next_delay_action([]) == "delay_complete"


def test_delay_asks_for_current_station():
    response = decide_next_delay_action(["current_station"])
    assert "currently reached" in response


def test_delay_asks_for_delay_minutes():
    response = decide_next_delay_action(["delay_minutes"])
    assert "How many minutes" in response


def test_post_prediction_advice_15_minutes():
    advice = post_prediction_advice(16)
    assert "15 minutes" in advice


def test_post_prediction_advice_under_15_minutes():
    advice = post_prediction_advice(5)
    assert "under 15 minutes" in advice