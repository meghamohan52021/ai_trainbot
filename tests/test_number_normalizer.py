import pytest

from number_normalizer import extract_delay_minutes


@pytest.mark.parametrize(
    "text, expected",
    [
        ("15", 15),
        ("15 minutes", 15),
        ("15 mins", 15),
        ("1 hour", 60),
        ("2 hours", 120),
        ("1 hour 15 minutes", 75),
        ("half an hour", 30),
        ("fifteen minutes", 15),
    ],
)
def test_extract_delay_minutes(text, expected):
    assert extract_delay_minutes(text) == expected


def test_extract_delay_minutes_returns_none_for_invalid_text():
    assert extract_delay_minutes("not sure") is None