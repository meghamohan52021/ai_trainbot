from nlp_engine import SpacyNLPEngine


def test_spacy_tokenisation():
    nlp = SpacyNLPEngine()
    analysis = nlp.analyse("My train got delayed at Southampton.")

    assert "train" in analysis.tokens
    assert "southampton" in analysis.tokens


def test_spacy_lemmatisation_has_delay():
    nlp = SpacyNLPEngine()
    analysis = nlp.analyse("My train got delayed.")

    assert "delay" in analysis.lemmas or "delayed" in analysis.tokens


def test_delay_language_detection():
    nlp = SpacyNLPEngine()
    assert nlp.has_delay_language("my train got delayed") is True


def test_ticket_language_detection():
    nlp = SpacyNLPEngine()
    assert nlp.has_ticket_language("I need a cheap ticket") is True


def test_similarity_returns_float():
    nlp = SpacyNLPEngine()
    score = nlp.similarity("train refund", "ticket compensation")
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0