import re

try:
    from number_parser import parse_number
except Exception:
    parse_number = None


BASIC_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    "hundred": 100,
}


def words_to_int(text: str):
    #Convert written numbers to integers
    text = str(text).lower().replace("-", " ").strip()

    if text.isdigit():
        return int(text)

    if parse_number:
        parsed = parse_number(text)
        if parsed is not None:
            return int(parsed)

    parts = text.split()
    total = 0
    current = 0
    matched = False

    for part in parts:
        if part not in BASIC_NUMBERS:
            continue
        matched = True
        value = BASIC_NUMBERS[part]
        if value == 100:
            current = max(current, 1) * 100
        else:
            current += value

    total += current
    return total if matched else None


def extract_delay_minutes(text: str):
    text_lower = str(text).lower().strip()

    if not text_lower:
        return None

    if text_lower.isdigit():
        return int(text_lower)

    #Common natural expressions first
    if re.search(r"\bhalf\s+(an\s+)?hour\b", text_lower):
        base = 30
        extra_match = re.search(r"\bhalf\s+(?:an\s+)?hour\s+(?:and\s+)?(\d+)\s*(?:minute|minutes|min|mins)\b", text_lower)
        if extra_match:
            return base + int(extra_match.group(1))
        return base

    if re.fullmatch(r"an\s+hour|a\s+hour|one\s+hour", text_lower):
        return 60

    #Hours with optional minutes:1 hour,1 hour 15 minutes,etc
    hour_match = re.search(r"\b(\d+|[a-zA-Z\- ]+?)\s*(hour|hours|hr|hrs)\b", text_lower)
    minute_match = re.search(r"\b(\d+|[a-zA-Z\- ]+?)\s*(minute|minutes|min|mins)\b", text_lower)

    total = 0
    found = False

    if hour_match:
        hour_text = hour_match.group(1).strip()
        if hour_text in {"a", "an"}:
            hours = 1
        else:
            hours = int(hour_text) if hour_text.isdigit() else words_to_int(hour_text)
        if hours is not None:
            total += hours * 60
            found = True

    if minute_match:
        minute_text = minute_match.group(1).strip()
        minutes = int(minute_text) if minute_text.isdigit() else words_to_int(minute_text)
        if minutes is not None:
            total += minutes
            found = True

    if found:
        return total

    #Written number only like fifteen
    written = words_to_int(text_lower)
    if written is not None:
        return written

    return None
