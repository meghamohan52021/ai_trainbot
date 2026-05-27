from temporal_parser import parse_natural_dates, extract_time_preferences


def test_parse_tomorrow_returns_one_date():
    dates = parse_natural_dates("tomorrow")
    assert len(dates) == 1
    assert isinstance(dates[0], str)


def test_parse_day_after_tomorrow_returns_one_date():
    dates = parse_natural_dates("day after tomorrow")
    assert len(dates) == 1
    assert isinstance(dates[0], str)


def test_extract_exact_time_3pm():
    prefs = extract_time_preferences("3pm")
    assert len(prefs) >= 1
    assert prefs[0]["type"] == "at"
    assert prefs[0]["time"] == "15:00"


def test_extract_morning_preference():
    prefs = extract_time_preferences("morning")
    assert len(prefs) >= 1
    assert prefs[0]["type"] == "between"
    assert prefs[0]["start"] == "07:00"
    assert prefs[0]["end"] == "11:59"


def test_extract_before_10am():
    prefs = extract_time_preferences("before 10am")
    assert len(prefs) >= 1
    assert prefs[0]["type"] == "before"
    assert prefs[0]["time"] == "10:00"


def test_extract_after_2pm():
    prefs = extract_time_preferences("after 2pm")
    assert len(prefs) >= 1
    assert prefs[0]["type"] == "after"
    assert prefs[0]["time"] == "14:00"