import re
from typing import Dict, Optional, List, Any, Tuple

from llm_client import LLMClient
from number_normalizer import extract_delay_minutes, words_to_int
from station_data import STATION_ALIASES
from temporal_parser import (
    parse_natural_dates,
    extract_time_preferences,
    infer_return_date_from_duration,
)
from entity_extractor import EntityExtractor
from intent_classifier import IntentClassifier
from nlu_result import NLUResult
from config import INTENT_MEDIUM_CONFIDENCE
from station_matcher import StationMatcher, StationMatch


class LLMParser:
    #Main parser class that combines regex, rules, 
    #and LLM fallback for robust extraction of structured data from user input

    def __init__(self):
        self.llm = LLMClient()
        self.entities = EntityExtractor()
        self.intent_classifier = IntentClassifier()
        self.station_matcher = StationMatcher(STATION_ALIASES)


    #Basic text processing
    def tokenize(self, text: str) -> List[str]:
        cleaned = text.lower()
        cleaned = re.sub(r"[?.,!]", " ", cleaned)
        return cleaned.split()


    #Intent detection with rules-based adjustments
    def understand(self, text: str, current_state: Optional[Dict[str, Any]] = None) -> NLUResult:
        current_state = current_state or {}
        lower = text.lower()

        pred = self.intent_classifier.predict(text)
        intent = pred.get("intent", "unknown")
        confidence = float(pred.get("confidence", 0.0))

        delay_words = [
            "delay", "delayed", "late", "arrival", "arrive",
            "reached", "current station", "minutes", "mins",
        ]
        if any(w in lower for w in delay_words):
            if confidence < 0.85:
                intent = "delay"
                confidence = max(confidence, 0.75)

        ticket_words = [
            "ticket", "tickets", "fare", "price", "cheapest",
            "journey", "travel", "return", "single", "one way",
            "from", "to", "go to", "going to",
        ]
        if any(w in lower for w in ticket_words):
            if intent != "delay" and confidence < 0.85:
                intent = "ticket"
                confidence = max(confidence, 0.75)

        return NLUResult(
            intent=intent,
            intent_confidence=confidence,
            entities={},
            entity_confidence={},
            source="tfidf_intent_classifier_plus_rules",
            needs_llm_fallback=confidence < INTENT_MEDIUM_CONFIDENCE,
            raw_text=text,
        )

    def detect_intent(self, text: str) -> str:
        return self.understand(text).intent

    # Public station helpers used by controller
    def match_station_with_status(self, text: str) -> StationMatch:
        return self.station_matcher.match(text)

    def find_station_in_text(self, text: str):
        match = self.station_matcher.match(text)
        return match.station if match.status == "exact" else None

    def find_all_stations(self, text: str) -> List[str]:
        match = self.station_matcher.match(text)
        if match.status == "exact" and match.station:
            return [match.station]
        if match.status == "ambiguous":
            return [c.station for c in match.candidates]
        return []

    #Ticket extraction
    def extract_ticket(self, text: str, current_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        current_state = current_state or {}
        text_lower = text.lower().strip()
        no_time_preference = {
            "no preference",
            "any time",
            "anytime",
            "no preferred time",
            "i don't mind",
            "i dont mind",
            "any",}

        extracted: Dict[str, Any] = {
            "from_station": None,
            "to_station": None,
            "journey_type": None,
            "depart_date": None,
            "depart_time_pref": None,
            "return_date": None,
            "return_time_pref": None,
            "duration_options": [],
            "station_ambiguity": None,
            "station_not_found": None,
        }

        #Journey type
        if any(x in text_lower for x in ["return", "come back", "coming back", "round trip", "round-trip"]):
            extracted["journey_type"] = "return"
        elif any(x in text_lower for x in ["single", "one way", "one-way", "oneway"]):
            extracted["journey_type"] = "single"

        raw_from, raw_to = self.extract_raw_route_phrases(text_lower)

        if raw_from:
            self._apply_station_match(extracted, "from_station", raw_from)

        if raw_to:
            self._apply_station_match(extracted, "to_station", raw_to)

        
        if not raw_from and not raw_to and not self._is_non_station_ticket_input(text_lower):
            station_match = self.station_matcher.match(text)

            if station_match.status == "exact":
                station = station_match.station

                if current_state.get("from_station") and not current_state.get("to_station"):
                    if station != current_state.get("from_station"):
                        extracted["to_station"] = station
                elif current_state.get("to_station") and not current_state.get("from_station"):
                    if station != current_state.get("to_station"):
                        extracted["from_station"] = station
                else:
                    #Do not guess unless the phrase contains a direction word
                    if re.search(r"\b(to|go to|going to|destination)\b", text_lower):
                        extracted["to_station"] = station
                    elif re.search(r"\b(from|leaving from|departing from|origin)\b", text_lower):
                        extracted["from_station"] = station
                    else:
                        extracted["from_station"] = station

            elif station_match.status == "ambiguous":
                target_slot = "to_station" if re.search(r"\b(to|go to|going to|destination)\b", text_lower) else "from_station"
                extracted["station_ambiguity"] = {
                    "slot": target_slot,
                    "raw_text": station_match.raw_text,
                    "candidates": [c.station for c in station_match.candidates],
                }
            elif station_match.status == "not_found" and self._looks_like_station_answer(text_lower):
                extracted["station_not_found"] = {
                    "slot": "station",
                    "raw_text": text.strip(),
                }

        #Natural date extraction
        dates = parse_natural_dates(text)
        if len(dates) >= 2:
            extracted["depart_date"] = dates[0]
            extracted["return_date"] = dates[1]
            if not extracted["journey_type"]:
                extracted["journey_type"] = "return"
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

        #Time preference extraction
        time_prefs = extract_time_preferences(text)
        if text_lower in no_time_preference:
            extracted["depart_time_pref"] = {"type": "any", "time": None}
        if time_prefs:
            if len(time_prefs) >= 2:
                extracted["depart_time_pref"] = time_prefs[0]
                extracted["return_time_pref"] = time_prefs[1]
                if not extracted["journey_type"]:
                    extracted["journey_type"] = "return"
            else:
                pref = time_prefs[0]
                if (
                    "come back" in text_lower
                    or "coming back" in text_lower
                    or "return" in text_lower
                    or extracted.get("return_date")
                    or current_state.get("return_date")
                ):
                    if current_state.get("depart_date") or extracted.get("depart_date"):
                        extracted["return_time_pref"] = pref
                    else:
                        extracted["depart_time_pref"] = pref
                else:
                    extracted["depart_time_pref"] = pref

        #Trip duration
        duration_options = self.extract_duration_options(text_lower)
        if duration_options:
            extracted["duration_options"] = duration_options
            if not extracted["journey_type"]:
                extracted["journey_type"] = "return"

        depart_for_duration = extracted.get("depart_date") or current_state.get("depart_date")
        inferred_return = infer_return_date_from_duration(depart_for_duration, text)
        if inferred_return:
            extracted["return_date"] = inferred_return
            extracted["journey_type"] = "return"

        #Safety: never return same station as origin and destination.
        if (
            extracted.get("from_station")
            and extracted.get("to_station")
            and extracted["from_station"] == extracted["to_station"]
        ):
            extracted["to_station"] = None

        #Optional LLM fallback only when almost nothing useful was extracted
        useful_values = [
            extracted["from_station"], extracted["to_station"], extracted["journey_type"],
            extracted["depart_date"], extracted["return_date"], extracted["depart_time_pref"],
            extracted["return_time_pref"], extracted["station_ambiguity"], extracted["station_not_found"],
        ]
        if not any(v not in (None, "", []) for v in useful_values):
            nlu = self.understand(text, current_state)
            if nlu.needs_llm_fallback:
                llm_data = self.llm.extract_structured_data(text, current_state)
                for key, value in llm_data.items():
                    if key in extracted and extracted[key] in (None, "", []):
                        extracted[key] = value

        return extracted

    def _apply_station_match(self, extracted: Dict[str, Any], slot: str, raw_text: str) -> None:
        match = self.station_matcher.match(raw_text)

        if match.status == "exact":
            extracted[slot] = match.station
        elif match.status == "ambiguous":
            extracted["station_ambiguity"] = {
                "slot": slot,
                "raw_text": match.raw_text,
                "candidates": [c.station for c in match.candidates],
            }
        elif match.status == "not_found":
            extracted["station_not_found"] = {
                "slot": slot,
                "raw_text": raw_text.strip(),
            }

    def extract_raw_route_phrases(self, text_lower: str) -> Tuple[Optional[str], Optional[str]]:
        #Stop before date/time/journey words
        stop = r"(?:\s+on\b|\s+at\b|\s+before\b|\s+after\b|\s+tomorrow\b|\s+today\b|\s+next\b|\s+return\b|\s+single\b|$)"

        
        m = re.search(rf"\bfrom\s+(.+?)\s+to\s+(.+?){stop}", text_lower)
        if m:
            return self._clean_station_phrase(m.group(1)), self._clean_station_phrase(m.group(2))

        
        m = re.search(rf"\b(?:go\s+to|going\s+to|travel\s+to|travelling\s+to|get\s+to|to)\s+(.+?)\s+from\s+(.+?){stop}", text_lower)
        if m:
            return self._clean_station_phrase(m.group(2)), self._clean_station_phrase(m.group(1))

        
        cleaned = re.sub(
            r"\b(i|we)\s+(want|need|would like|wanna)\s+(to\s+)?(go|travel|get|book)?\s*",
            " ",
            text_lower,
        ).strip()
        m = re.search(rf"^(.+?)\s+to\s+(.+?){stop}", cleaned)
        if m:
            return self._clean_station_phrase(m.group(1)), self._clean_station_phrase(m.group(2))

        
        m = re.search(rf"\b(?:go\s+to|going\s+to|travel\s+to|travelling\s+to|get\s+to|to)\s+(.+?){stop}", text_lower)
        if m:
            return None, self._clean_station_phrase(m.group(1))

        
        m = re.search(rf"\bfrom\s+(.+?){stop}", text_lower)
        if m:
            return self._clean_station_phrase(m.group(1)), None

        return None, None

    @staticmethod
    def _clean_station_phrase(value: str) -> str:
        value = re.sub(r"\b(i|we|want|need|would|like|to|go|going|travel|travelling|get|book|a|an|the|ticket|train)\b", " ", value)
        value = re.sub(r"\s+", " ", value).strip(" ,.!?")
        return value


    @staticmethod
    def _is_non_station_ticket_input(text_lower: str) -> bool:
            # Prevent dates/times/random full sentences from being reported as unknown stations
        if not text_lower:
            return True

        clean = re.sub(r"[^a-z0-9: ]+", " ", text_lower.lower())
        clean = re.sub(r"\s+", " ", clean).strip()

        #Direct journey-type answers
        if clean in {
            "single", "return", "one way", "one way ticket",
            "yes", "no", "y", "n", "correct", "wrong",
            "time", "date", "journey type", "ticket type",
        }:
            return True

        #Date/time expressions should not be station matched
        date_time_words = {
            "today", "tomorrow", "day after tomorrow", "next",
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
            "morning", "afternoon", "evening", "night",
            "after", "before", "around", "about", "at", "pm", "am",
        }

        if clean in date_time_words:
            return True

        tokens = set(clean.split())
        if tokens and tokens.issubset(date_time_words):
            return True

        #Phrases such as 'after 2pm', 'before 10am', 'next tuesday'
        if re.search(r"\b(after|before|around|about|at)\s+\d{1,2}(:\d{2})?\s*(am|pm)?\b", clean):
            return True
        if re.search(r"\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", clean):
            return True

        return False

    @staticmethod
    def _looks_like_station_answer(text_lower: str) -> bool:
        #Prevent dates/times/random full sentences from being reported as unknown stations
        if not text_lower or len(text_lower.split()) > 5:
            return False
        if any(w in text_lower for w in ["tomorrow", "today", "single", "return", "after", "before", "morning", "afternoon", "evening"]):
            return False
        return bool(re.search(r"[a-z]", text_lower))


    #Delay extraction
    def extract_delay(self, text: str, current_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        current_state = current_state or {}
        text_lower = text.lower().strip()

        extracted = {
            "train_id": None,
            "current_station": None,
            "delay_minutes": None,
            "destination": None,
            "station_ambiguity": None,
            "station_not_found": None,
        }

        entity_data = self.entities.extract(text)
        roles = entity_data.get("station_roles", {})

        extracted["train_id"] = entity_data.get("train_id")
        extracted["delay_minutes"] = entity_data.get("delay_minutes")

        #Try explicit station phrases first
        current_raw = self._extract_raw_current_station(text_lower)
        dest_raw = self._extract_raw_delay_destination(text_lower)

        if current_raw:
            self._apply_delay_station_match(extracted, "current_station", current_raw)
        elif roles.get("current_station"):
            extracted["current_station"] = roles.get("current_station")

        if dest_raw:
            self._apply_delay_station_match(extracted, "destination", dest_raw)
        elif roles.get("destination") or roles.get("to_station"):
            extracted["destination"] = roles.get("destination") or roles.get("to_station")

        if not extracted["train_id"]:
            stop_words = {"is", "a", "the", "my", "to", "at", "in", "on", "by", "an", "not", "was", "has"}
            train_match = re.search(r"\b(train|service|operator)\s+([a-zA-Z0-9\-]+)", text_lower)
            if train_match and train_match.group(2) not in stop_words:
                extracted["train_id"] = train_match.group(2).upper()
            else:
                headcode_match = re.search(r"\b([0-9][a-zA-Z][0-9]{2})\b", text_lower)
                if headcode_match:
                    extracted["train_id"] = headcode_match.group(1).upper()

        if extracted["delay_minutes"] is None:
            extracted["delay_minutes"] = extract_delay_minutes(text_lower)

        useful_values = [
            extracted["train_id"], extracted["current_station"], extracted["delay_minutes"],
            extracted["destination"], extracted["station_ambiguity"], extracted["station_not_found"],
        ]
        if not any(v not in (None, "", []) for v in useful_values):
            nlu = self.understand(text, current_state)
            if nlu.needs_llm_fallback:
                llm_data = self.llm.extract_structured_data(text, current_state)
                for key, value in llm_data.items():
                    if key in extracted and extracted[key] in (None, "", []):
                        extracted[key] = value

        return extracted

    def _apply_delay_station_match(self, extracted: Dict[str, Any], slot: str, raw_text: str) -> None:
        match = self.station_matcher.match(raw_text)
        if match.status == "exact":
            extracted[slot] = match.station
        elif match.status == "ambiguous":
            extracted["station_ambiguity"] = {
                "slot": slot,
                "raw_text": match.raw_text,
                "candidates": [c.station for c in match.candidates],
            }
        else:
            extracted["station_not_found"] = {"slot": slot, "raw_text": raw_text.strip()}

    @staticmethod
    def _extract_raw_current_station(text_lower: str) -> Optional[str]:
        patterns = [
            r"\bcurrent\s+station\s+is\s+(.+?)(?:\s+going\s+to|\s+to\s+|$)",
            r"\bcurrently\s+at\s+(.+?)(?:\s+going\s+to|\s+to\s+|$)",
            r"\bnow\s+at\s+(.+?)(?:\s+going\s+to|\s+to\s+|$)",
            r"\bat\s+(.+?)(?:\s+going\s+to|\s+to\s+|$)",
            r"\breached\s+(.+?)(?:\s+going\s+to|\s+to\s+|$)",
        ]
        for pattern in patterns:
            m = re.search(pattern, text_lower)
            if m:
                return LLMParser._clean_station_phrase(m.group(1))
        return None

    @staticmethod
    def _extract_raw_delay_destination(text_lower: str) -> Optional[str]:
        patterns = [
            r"\bdestination\s+is\s+(.+?)$",
            r"\bgoing\s+to\s+(.+?)$",
            r"\sto\s+(.+?)$",
        ]
        for pattern in patterns:
            m = re.search(pattern, text_lower)
            if m:
                return LLMParser._clean_station_phrase(m.group(1))
        return None


    #Public extraction method called by controller, which decides based on intent which extraction to run
    def extract(self, text: str, current_state: Optional[Dict[str, Any]], task: str = "ticket") -> Dict[str, Any]:
        if task == "delay":
            return self.extract_delay(text, current_state)
        return self.extract_ticket(text, current_state)


    def extract_current_station(self, text_lower: str):
        raw = self._extract_raw_current_station(text_lower)
        return self.find_station_in_text(raw) if raw else None

    def extract_destination_station(self, text_lower: str):
        raw = self._extract_raw_delay_destination(text_lower)
        return self.find_station_in_text(raw) if raw else None

    
    #Duration helpers
    def extract_duration_options(self, text_lower: str) -> List[int]:
        options = []

        or_match = re.search(r"\b([a-zA-Z0-9\-]+)\s+or\s+([a-zA-Z0-9\-]+)\s+days?\b", text_lower)
        if or_match:
            first = words_to_int(or_match.group(1))
            second = words_to_int(or_match.group(2))
            if first is not None:
                options.append(first)
            if second is not None:
                options.append(second)

        single_match = re.search(r"\bfor\s+([a-zA-Z0-9\-]+)\s+days?\b", text_lower)
        if single_match:
            value = words_to_int(single_match.group(1))
            if value is not None and value not in options:
                options.append(value)

        return options

    @staticmethod
    def _to_24h(hour_str, minute_str=None, meridiem=None):
        hour = int(hour_str)
        minute = int(minute_str) if minute_str else 0

        if meridiem:
            meridiem = meridiem.lower()
            if meridiem == "pm" and hour != 12:
                hour += 12
            if meridiem == "am" and hour == 12:
                hour = 0

        return f"{hour:02d}:{minute:02d}"
