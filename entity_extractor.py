import re
from rapidfuzz import process, fuzz

from station_data import STATION_ALIASES
from config import FUZZY_STATION_THRESHOLD
from number_normalizer import extract_delay_minutes


class EntityExtractor:
    def __init__(self):
        self.alias_to_station = STATION_ALIASES
        self.aliases = list(STATION_ALIASES.keys())

    def extract(self, text: str) -> dict:
        return {
            "stations": self.extract_stations(text),
            "station_roles": self.extract_station_roles(text),
            "train_id": self.extract_train_id(text),
            "delay_minutes": extract_delay_minutes(text),
            "journey_type": self.extract_journey_type(text),
        }

    def extract_journey_type(self, text: str):
        t = text.lower()
        if any(x in t for x in ["return", "round trip", "round-trip", "come back", "coming back"]):
            return "return"
        if any(x in t for x in ["single", "one way", "one-way", "oneway"]):
            return "single"
        return None

    def extract_train_id(self, text: str):
        t = text.lower()

        match = re.search(r"\b(?:train|service)\s+([0-9][a-zA-Z][0-9]{2}|[a-zA-Z0-9\-]+)\b", t)
        if match:
            value = match.group(1)
            if value not in {"is", "at", "to", "delayed", "late"}:
                return value.upper()

        headcode = re.search(r"\b([0-9][a-zA-Z][0-9]{2})\b", t)
        if headcode:
            return headcode.group(1).upper()

        return None

    def extract_stations(self, text: str):
        text_lower = text.lower()
        found = []

        aliases = sorted(self.alias_to_station.items(), key=lambda x: len(x[0]), reverse=True)

        for alias, official in aliases:
            pattern = r"\b" + re.escape(alias.lower()) + r"\b"
            if re.search(pattern, text_lower) and official not in found:
                found.append(official)

        # fuzzy fallback only if exact found nothing or user likely misspelled a station
        if not found:
            words = re.findall(r"[a-zA-Z][a-zA-Z\s]{2,}", text_lower)
            for chunk in words:
                match = process.extractOne(chunk.strip(), self.aliases, scorer=fuzz.WRatio)
                if match and match[1] >= FUZZY_STATION_THRESHOLD:
                    official = self.alias_to_station[match[0]]
                    if official not in found:
                        found.append(official)

        return found

    def extract_station_roles(self, text: str):
        t = text.lower()
        roles = {}

        from_to = re.search(r"\bfrom\s+(.+?)\s+to\s+(.+?)(?:\s+on\b|\s+at\b|\s+before\b|\s+after\b|$)", t)
        if from_to:
            roles["from_station"] = self._best_station(from_to.group(1))
            roles["to_station"] = self._best_station(from_to.group(2))

        current_patterns = [
            r"\bcurrently\s+at\s+(.+?)(?:\s+going\s+to|\s+to|$)",
            r"\bcurrent\s+station\s+is\s+(.+?)(?:\s+going\s+to|\s+to|$)",
            r"\bnow\s+at\s+(.+?)(?:\s+going\s+to|\s+to|$)",
            r"\bat\s+(.+?)(?:\s+going\s+to|\s+to|$)",
            r"\breached\s+(.+?)(?:\s+going\s+to|\s+to|$)",
        ]

        for pattern in current_patterns:
            m = re.search(pattern, t)
            if m:
                roles["current_station"] = self._best_station(m.group(1))
                break

        destination_patterns = [
            r"\bgoing\s+to\s+(.+?)(?:\s+on\b|\s+at\b|\s+before\b|\s+after\b|$)",
            r"\bdestination\s+is\s+(.+?)$",
            r"\bto\s+(.+?)$",
        ]

        for pattern in destination_patterns:
            m = re.search(pattern, t)
            if m:
                roles["destination"] = self._best_station(m.group(1))
                break

        return {k: v for k, v in roles.items() if v}

    def _best_station(self, text: str):
        stations = self.extract_stations(text)
        if stations:
            return stations[0]

        match = process.extractOne(text.lower().strip(), self.aliases, scorer=fuzz.WRatio)
        if match and match[1] >= FUZZY_STATION_THRESHOLD:
            return self.alias_to_station[match[0]]

        return None