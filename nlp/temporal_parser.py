from typing import Optional, Tuple
import re
from datetime import timedelta, date
from config import now_london


TIME_PREFS = {
    "morning": {"type": "between", "start": "07:00", "end": "11:59"},
    "afternoon": {"type": "between", "start": "12:00", "end": "17:59"},
    "evening": {"type": "between", "start": "18:00", "end": "21:59"},
    "night": {"type": "between", "start": "20:00", "end": "23:59"},
}

MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def _future_date(day: int, month: int, year: Optional[int] = None) -> Optional[date]:
    today = now_london().date()
    if year is None:
        year = today.year
    try:
        candidate = date(year, month, day)
    except ValueError:
        return None
    if candidate < today and year == today.year:
        try:
            candidate = date(today.year + 1, month, day)
        except ValueError:
            return None
    return candidate


def _next_weekday(target_index: int) -> date:
    today = now_london().date()
    days_ahead = (target_index - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return today + timedelta(days=days_ahead)


def parse_natural_dates(text: str):
    text_lower = text.lower().strip()

    if text_lower in {
        "single", "return", "one way", "one-way", "yes", "no", "y", "n",
        "time", "date", "morning", "afternoon", "evening", "night",
        "anytime", "any time", "no preference",
    }:
        return []

    found: list[str] = []
    today = now_london().date()

    def add(d):
        if d is None:
            return
        iso = d.isoformat()
        if iso not in found:
            found.append(iso)

    #ISO dates: 2026-07-15
    for match in re.finditer(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", text_lower):
        y, m, d = map(int, match.groups())
        add(_future_date(d, m, y))

    #Slash dates: 15/07 or 15/07/2026
    for match in re.finditer(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", text_lower):
        d = int(match.group(1))
        m = int(match.group(2))
        y_text = match.group(3)
        year = None
        if y_text:
            year = int(y_text)
            if year < 100:
                year += 2000
        add(_future_date(d, m, year))

    #Relative dates
    if re.search(r"\bday after tomorrow\b", text_lower):
        add(today + timedelta(days=2))
    elif re.search(r"\btomorrow\b", text_lower):
        add(today + timedelta(days=1))
    elif re.search(r"\btoday\b", text_lower):
        add(today)

    #next Tuesday or Tuesday
    for weekday, index in WEEKDAYS.items():
        if re.search(rf"\b(?:next\s+)?{weekday}\b", text_lower):
            add(_next_weekday(index))

    #15 July / 15th July / 15 July 2026
    month_names = "|".join(MONTHS.keys())
    pattern = rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({month_names})(?:\s+(20\d{{2}}))?\b"
    for match in re.finditer(pattern, text_lower):
        day = int(match.group(1))
        month = MONTHS[match.group(2)]
        year = int(match.group(3)) if match.group(3) else None
        add(_future_date(day, month, year))

    return found


def extract_time_preferences(text: str):
    text_lower = text.lower().strip()
    prefs = []

    if text_lower in {"no preference", "any time", "anytime", "any", "i don't mind", "i dont mind"}:
        return [{"type": "any", "time": None}]

    for word, value in TIME_PREFS.items():
        if re.search(rf"\b{word}\b", text_lower):
            prefs.append(value)

    before = re.search(r"\bbefore\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b(?!\s*days?\b)", text_lower)
    after = re.search(r"\bafter\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b(?!\s*days?\b)", text_lower)
    around = re.search(r"\b(around|about|at)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", text_lower)
    plain_time = re.search(r"^\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s*$", text_lower)

    if before:
        prefs.append({"type": "before", "time": to_24h(before.group(1), before.group(2), before.group(3))})
    if after:
        prefs.append({"type": "after", "time": to_24h(after.group(1), after.group(2), after.group(3))})
    if around:
        prefs.append({"type": "at", "time": to_24h(around.group(2), around.group(3), around.group(4))})
    if plain_time:
        prefs.append({"type": "at", "time": to_24h(plain_time.group(1), plain_time.group(2), plain_time.group(3))})

    #Embedded time like "tomorrow 3pm" or "return time 11am"
    if not prefs:
        embedded = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", text_lower)
        if embedded:
            prefs.append({"type": "at", "time": to_24h(embedded.group(1), embedded.group(2), embedded.group(3))})

    return prefs


def infer_return_date_from_duration(depart_date: str, text: str):
    if not depart_date:
        return None

    match = re.search(r"\b(?:back|return|come back)\s+(?:after|in)?\s*(\d+)\s+days?\b", text.lower())
    if not match:
        match = re.search(r"\bfor\s+(\d+)\s+days?\b", text.lower())
    if not match:
        return None

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
