from nlp.parser import LLMParser


def test_ticket_intent_detected():
    parser = LLMParser()
    result = parser.understand("I want to go to Norwich")
    assert result.intent == "ticket"


def test_delay_intent_detected():
    parser = LLMParser()
    result = parser.understand("my train got delayed")
    assert result.intent == "delay"


def test_delay_intent_takes_priority_over_ticket_words():
    parser = LLMParser()
    result = parser.understand("I want to go to Norwich but my train got delayed")
    assert result.intent == "delay"


def test_extract_destination_from_go_to_phrase():
    parser = LLMParser()
    extracted = parser.extract(
        "I want to go to Norwich",
        current_state={},
        task="ticket",
    )
    assert extracted["to_station"] == "NORWICH"


def test_station_phrase_does_not_include_delay_text():
    parser = LLMParser()
    raw_from, raw_to = parser.extract_raw_route_phrases(
        "i want to go to norwich but my train got delayed"
    )
    assert raw_to == "norwich"


def test_extract_ticket_single_journey_type():
    parser = LLMParser()
    extracted = parser.extract(
        "single",
        current_state={},
        task="ticket",
    )
    assert extracted["journey_type"] == "single"


def test_extract_ticket_return_journey_type():
    parser = LLMParser()
    extracted = parser.extract(
        "return",
        current_state={},
        task="ticket",
    )
    assert extracted["journey_type"] == "return"


def test_extract_delay_minutes_from_delay_flow():
    parser = LLMParser()
    extracted = parser.extract(
        "15 mins",
        current_state={},
        task="delay",
    )
    assert extracted["delay_minutes"] == 15


def test_extract_delay_current_station():
    parser = LLMParser()
    extracted = parser.extract(
        "currently at Southampton Central",
        current_state={},
        task="delay",
    )
    assert extracted["current_station"] == "SOUTHAMPTON CENTRAL"


def test_extract_delay_destination():
    parser = LLMParser()
    extracted = parser.extract(
        "going to Waterloo London",
        current_state={},
        task="delay",
    )
    assert extracted["destination"] == "WATERLOO LONDON"