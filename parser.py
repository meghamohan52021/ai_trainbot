import re

from matplotlib import dates
from llm_client import LLMClient
from station_data import STATION_ALIASES


class LLMParser:
    """
    Rule-based NLP/NLU parser.

    Version 1(without llm):
    - tokenisation
    - keyword intent recognition
    - regex slot extraction
    - station alias matching
    """

    def __init__(self):
        self.llm = LLMClient()

    def tokenize(self, text: str) -> list:
        cleaned = text.lower()
        cleaned = cleaned.replace("?", "").replace(".", "").replace(",", "")
        return cleaned.split()

    def detect_intent(self, text: str) -> str:
        tokens = self.tokenize(text)
        text_lower = text.lower()

        delay_keywords = [
            "delay", "delayed", "late", "arrival", "arrive",
            "reached", "current", "minutes", "mins"
        ]

        ticket_keywords = [
            "ticket", "tickets", "fare", "price", "cheapest",
            "journey", "travel", "return", "single", "from", "to"
        ]

        for word in delay_keywords:
            if word in tokens or word in text_lower:
                return "delay"

        for word in ticket_keywords:
            if word in tokens or word in text_lower:
                return "ticket"

        return "faq"

    def extract_ticket(self, text: str, current_state: dict) -> dict:
        text_lower = text.lower().strip()

        extracted = {
            "from_station": None,
            "to_station": None,
            "journey_type": None,
            "depart_date": None,
            "depart_time_pref": None,
            "return_date": None,
            "return_time_pref": None,
            "duration_options": [],
        }

        if (
            "return" in text_lower
            or "come back" in text_lower
            or "round trip" in text_lower
            or "round-trip" in text_lower
        ):
            extracted["journey_type"] = "return"

        elif (
            "single" in text_lower
            or "one way" in text_lower
            or "one-way" in text_lower
            or "oneway" in text_lower
        ):
            extracted["journey_type"] = "single"


        from_to_match = re.search(
            r"from\s+([a-zA-Z\s]+?)\s+to\s+([a-zA-Z\s]+)",
            text_lower
        )

        if from_to_match:
            extracted["from_station"] = self.find_station_in_text(from_to_match.group(1))
            extracted["to_station"] = self.find_station_in_text(from_to_match.group(2))

        if not extracted["from_station"] or not extracted["to_station"]:
            found_stations = self.find_all_stations(text_lower)

            if len(found_stations) >= 1 and not extracted["from_station"]:
                if current_state.get("from_station") is None:
                    extracted["from_station"] = found_stations[0]

            if len(found_stations) >= 2 and not extracted["to_station"]:
                if current_state.get("to_station") is None:
                    extracted["to_station"] = found_stations[1]

            if len(found_stations) == 1 and not extracted["to_station"]:
                if current_state.get("from_station") is not None:
                    extracted["to_station"] = found_stations[0]

        dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text_lower)

        if len(dates) >= 2:
            extracted["depart_date"] = dates[0]
            extracted["return_date"] = dates[1]

        elif len(dates) == 1:
            only_date = dates[0]
            if (
                current_state.get("journey_type") == "return"
                and current_state.get("depart_date") not in (None, "", [])
                and current_state.get("return_date") in (None, "", [])
            ):
                extracted["return_date"] = only_date
            else:
                extracted["depart_date"] = only_date


        before_match = re.search(r"before\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text_lower)
        after_match = re.search(r"after\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text_lower)
        at_match = re.search(r"at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text_lower)

        if before_match:
            extracted["depart_time_pref"] = {
                "type": "before",
                "time": self._to_24h(before_match.group(1), before_match.group(2), before_match.group(3))
            }

        if after_match:
            if "come back" in text_lower or len(dates) >= 2 or current_state.get("return_date"):
                extracted["return_time_pref"] = {
                    "type": "after",
                    "time": self._to_24h(after_match.group(1), after_match.group(2), after_match.group(3))
                }
            else:
                extracted["depart_time_pref"] = {
                    "type": "after",
                    "time": self._to_24h(after_match.group(1), after_match.group(2), after_match.group(3))
                }

        if at_match and not extracted["depart_time_pref"]:
            extracted["depart_time_pref"] = {
                "type": "at",
                "time": self._to_24h(at_match.group(1), at_match.group(2), at_match.group(3))
            }

        duration_match = re.search(r"(\d+)\s+or\s+(\d+)\s+days", text_lower)
        if duration_match:
            extracted["duration_options"] = [
                int(duration_match.group(1)),
                int(duration_match.group(2))
            ]
            if not extracted["journey_type"]:
                extracted["journey_type"] = "return"

        single_duration = re.search(r"for\s+(\d+)\s+days", text_lower)
        if single_duration and not extracted["duration_options"]:
            extracted["duration_options"] = [int(single_duration.group(1))]
            if not extracted["journey_type"]:
                extracted["journey_type"] = "return"

        if "my native" in text_lower or "go home" in text_lower or "going home" in text_lower:
            if not extracted["journey_type"]:
                extracted["journey_type"] = "return"

        llm_data = self.llm.extract_structured_data(text, current_state)
        for key, value in llm_data.items():
            if key in extracted and not extracted[key]:
                extracted[key] = value

        return extracted

    def extract_delay(self, text: str, current_state: dict) -> dict:
        text_lower = text.lower().strip()

        extracted = {
            "train_id": None,
            "current_station": None,
            "delay_minutes": None,
            "destination": None,
        }

        _STOP_WORDS = {"is", "a", "the", "my", "to", "at", "in", "on", "by", "an", "not", "was", "has"}
        train_match = re.search(r"\b(train|service|operator)\s+([a-zA-Z0-9\-]+)", text_lower)
        if train_match and train_match.group(2) not in _STOP_WORDS:
            extracted["train_id"] = train_match.group(2).upper()
        else:
            # UK headcode pattern e.g. 1W67
            headcode_match = re.search(r"\b([0-9][a-zA-Z][0-9]{2})\b", text_lower)
            if headcode_match:
                extracted["train_id"] = headcode_match.group(1).upper()
            else:
                _NOT_TRAIN_ID = {"i", "im", "my", "me", "it", "its", "delayed",
                                 "late", "running", "slow", "train", "service"}
                words = set(re.findall(r"\w+", text_lower))
                if (not self.find_all_stations(text_lower)
                        and not re.match(r"^\s*\d+\s*$", text_lower)
                        and len(words) <= 3
                        and not words.intersection(_NOT_TRAIN_ID)):
                    extracted["train_id"] = text.strip()

        delay_match = re.search(r"(\d+)\s*(minute|minutes|min|mins)", text_lower)
        if delay_match:
            extracted["delay_minutes"] = int(delay_match.group(1))
        elif re.match(r"^\s*\d+\s*$", text_lower):
            extracted["delay_minutes"] = int(text_lower.strip())

        current_station = self.extract_current_station(text_lower)
        if current_station:
            extracted["current_station"] = current_station

        destination = self.extract_destination_station(text_lower)
        if destination:
            extracted["destination"] = destination

        found_stations = self.find_all_stations(text_lower)

        if found_stations:
            current_known = current_state.get("current_station") not in (None, "", [])
            if extracted["current_station"] is None:
                if not current_known:
                    extracted["current_station"] = found_stations[0]
                else:
                    # current_station already set, lone station must be the destination
                    extracted["destination"] = found_stations[0]

            if extracted["destination"] is None:
                for station in found_stations:
                    if station != extracted["current_station"]:
                        extracted["destination"] = station
                        break

        return extracted

    def extract_current_station(self, text_lower: str):
        patterns = [
            r"current\s+station\s+is\s+([a-zA-Z\s]+?)(?:\s+to\s+|\s+going\s+to\s+|$)",
            r"currently\s+at\s+([a-zA-Z\s]+?)(?:\s+to\s+|\s+going\s+to\s+|$)",
            r"now\s+at\s+([a-zA-Z\s]+?)(?:\s+to\s+|\s+going\s+to\s+|$)",
            r"at\s+([a-zA-Z\s]+?)(?:\s+to\s+|\s+going\s+to\s+|$)",
            r"reached\s+([a-zA-Z\s]+?)(?:\s+to\s+|\s+going\s+to\s+|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                station = self.find_station_in_text(match.group(1))
                if station:
                    return station

        return None

    def extract_destination_station(self, text_lower: str):
        patterns = [
            r"destination\s+is\s+([a-zA-Z\s]+)$",
            r"going\s+to\s+([a-zA-Z\s]+)$",
            r"\sto\s+([a-zA-Z\s]+)$",
        ]

        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                station = self.find_station_in_text(match.group(1))
                if station:
                    return station

        return None

    def extract(self, text: str, current_state: dict, task: str = "ticket") -> dict:
        if task == "delay":
            return self.extract_delay(text, current_state)

        return self.extract_ticket(text, current_state)

    def find_station_in_text(self, text: str):
        text_lower = text.lower().strip()

        #Matching longer aliases first, so "london waterloo" is chosen before "london"
        aliases = sorted(STATION_ALIASES.items(), key=lambda item: len(item[0]), reverse=True)

        for alias, official_name in aliases:
            if alias in text_lower or official_name.lower() in text_lower:
                return official_name

        return None

    def find_all_stations(self, text: str) -> list:
        found = []
        aliases = sorted(STATION_ALIASES.items(), key=lambda item: len(item[0]), reverse=True)

        for alias, official_name in aliases:
            is_crs = len(alias) == 3 and alias.isalpha()
            if is_crs:
                # CRS codes: match at word-boundary start so "wat" hits "waterloo"
                # but not mid-word like "ain" inside "train"
                m = re.search(r"\b" + re.escape(alias) + r"(\w*)", text)
                matched = bool(m)
                if matched and m.group(1) and any(alias + m.group(1) in on.lower() for on in found):
                    matched = False
            else:
                # Full names: require full word boundaries to stop "leigh" matching inside "eastleigh"
                matched = bool(
                    re.search(r"\b" + re.escape(alias) + r"\b", text) or
                    re.search(r"\b" + re.escape(official_name.lower()) + r"\b", text)
                )
            if matched and official_name not in found:
                found.append(official_name)

        return found

    @staticmethod
    def _to_24h(hour_str, minute_str, meridiem):
        hour = int(hour_str)
        minute = int(minute_str) if minute_str else 0

        if meridiem:
            meridiem = meridiem.lower()

            if meridiem == "pm" and hour != 12:
                hour += 12

            if meridiem == "am" and hour == 12:
                hour = 0

        return f"{hour:02d}:{minute:02d}"

