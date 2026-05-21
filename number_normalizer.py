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
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90
}


def words_to_int(text: str):
    text = text.lower().replace("-", " ").strip()

    if text.isdigit():
        return int(text)

    if parse_number:
        parsed = parse_number(text)
        if parsed is not None:
            return int(parsed)

    parts = text.split()
    total = 0
    matched = False

    for part in parts:
        if part in BASIC_NUMBERS:
            total += BASIC_NUMBERS[part]
            matched = True

    return total if matched else None


def extract_delay_minutes(text: str):
    text_lower = text.lower()

    digit_match = re.search(r"\b(\d+)\s*(minute|minutes|min|mins)\b", text_lower)
    if digit_match:
        return int(digit_match.group(1))

    word_match = re.search(
        r"\b([a-zA-Z\- ]+?)\s*(minute|minutes|min|mins)\b",
        text_lower
    )
    if word_match:
        return words_to_int(word_match.group(1))

    if text_lower.strip().isdigit():
        return int(text_lower.strip())

    return None