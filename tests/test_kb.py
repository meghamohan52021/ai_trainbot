from unittest.mock import patch

from kb import KnowledgeBase


FAKE_KB_ROWS = [
    {
        "keyword": "delay repay",
        "synonyms": "compensation, late train, refund for delay",
        "answer": "You may be eligible for Delay Repay if your train is delayed.",
    },
    {
        "keyword": "railcard",
        "synonyms": "student discount, young persons railcard",
        "answer": "Railcards can reduce eligible fares by around one third.",
    },
    {
        "keyword": "lost property",
        "synonyms": "lost item, left bag, missing luggage",
        "answer": "Contact the train operator's lost property office.",
    },
]


@patch("kb.get_all_knowledge", return_value=FAKE_KB_ROWS)
def test_kb_exact_keyword_match(mock_fetch):
    kb = KnowledgeBase()
    answer = kb.search("what is delay repay?")
    assert "Delay Repay" in answer


@patch("kb.get_all_knowledge", return_value=FAKE_KB_ROWS)
def test_kb_synonym_match(mock_fetch):
    kb = KnowledgeBase()
    answer = kb.search("can I get compensation?")
    assert "Delay Repay" in answer


@patch("kb.get_all_knowledge", return_value=FAKE_KB_ROWS)
def test_kb_fuzzy_typo_match(mock_fetch):
    kb = KnowledgeBase()
    answer = kb.search("railcrd discount")
    assert "Railcards" in answer


@patch("kb.get_all_knowledge", return_value=FAKE_KB_ROWS)
def test_kb_short_greeting_should_not_return_random_answer(mock_fetch):
    kb = KnowledgeBase()
    answer = kb.search("hi")
    assert answer is None