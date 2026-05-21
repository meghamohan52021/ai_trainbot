import re
from datetime import timedelta
import dateparser
from dateparser.search import search_dates

from config import now_london


TIME_PREFS = {
    "morning": {"type": "between", "start": "07:00", "end": "11:59"},
    "afternoon": {"type": "between", "start": "12:00", "end": "17:59"},
    "evening": {"type": "between", "start": "18:00", "end": "21:59"},
    "night": {"type": "between", "start": "20:00", "end": "23:59"},
}


def _settings():
    return {
        "RELATIVE_BASE": now_london(),
        "PREFER_DATES_FROM": "future",
        "DATE_ORDER": "DMY",
        "TIMEZONE": "Europe/London",
        "RETURN_AS_TIMEZONE_AWARE": True,
    }


def parse_natural_dates(text: str):
    # Quick check for common non-date answers to avoid unnecessary parsing
    text_lower = text.lower().strip()

    non_date_answers = {
        "single", "return", "one way", "one-way", "yes", "no",
        "y", "n", "time", "date", "morning", "afternoon",
        "evening", "night", "after", "before", "anytime",
        "any time", "no preference"
    }

    if text_lower in non_date_answers:
        return []

    date_cue_pattern = r"""
        \b(
            today|tomorrow|day\s+after\s+tomorrow|
            next|this|
            monday|tuesday|wednesday|thursday|friday|saturday|sunday|
            jan|january|feb|february|mar|march|apr|april|may|jun|june|
            jul|july|aug|august|sep|sept|september|oct|october|
            nov|november|dec|december
        )\b
        |
        \b\d{4}-\d{2}-\d{2}\b
        |
        \b\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?\b
        |
        \b\d{1,2}(st|nd|rd|th)?\s+
        (jan|january|feb|february|mar|march|apr|april|may|jun|june|
        jul|july|aug|august|sep|sept|september|oct|october|
        nov|november|dec|december)\b
    """

    if not re.search(date_cue_pattern, text_lower, re.VERBOSE):
        return []

    results = search_dates(text, settings=_settings()) or []
    dates = []

    ignored_phrases = {
        "single", "return", "time", "date", "yes", "no",
        "morning", "afternoon", "evening", "night"
    }

    for phrase, dt in results:
        if phrase.lower().strip() in ignored_phrases:
            continue

        iso = dt.date().isoformat()
        if iso not in dates:
            dates.append(iso)

    return dates


def extract_time_preferences(text: str):
    text_lower = text.lower()
    prefs = []

    for word, value in TIME_PREFS.items():
        if word in text_lower:
            prefs.append(value)

    before = re.search(r"\bbefore\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", text_lower)
    after = re.search(r"\bafter\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", text_lower)
    around = re.search(r"\b(around|about|at)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", text_lower)
    plain_time = re.search(r"^\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s*$", text_lower)

    if plain_time:
        prefs.append({
            "type": "at",
            "time": to_24h(
                plain_time.group(1),
                plain_time.group(2),
                plain_time.group(3)
            )
        })

    if before:
        prefs.append({"type": "before", "time": to_24h(before.group(1), before.group(2), before.group(3))})

    if after:
        prefs.append({"type": "after", "time": to_24h(after.group(1), after.group(2), after.group(3))})

    if around:
        prefs.append({"type": "at", "time": to_24h(around.group(2), around.group(3), around.group(4))})

    return prefs


def infer_return_date_from_duration(depart_date: str, text: str):
    if not depart_date:
        return None

    match = re.search(r"\b(?:back|return|come back)\s+(?:after|in)?\s*(\d+)\s+days?\b", text.lower())
    if not match:
        match = re.search(r"\bfor\s+(\d+)\s+days?\b", text.lower())

    if not match:
        return None

    from datetime import date
    start = date.fromisoformat(depart_date)
    return (start + timedelta(days=int(match.group(1)))).isoformat()


def to_24h(hour_str, minute_str=None, meridiem=None):
    hour = int(hour_str)
    minute = int(minute_str) if minute_str else 0

    if meridiem:
        meridiem = meridiem.lower()
        if meridiem == "pm" and hour != 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0

    return f"{hour:02d}:{minute:02d}"