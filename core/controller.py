from typing import Any, Dict, Optional

from core.state import ChatState, JourneyState, DelayState
from core.validation import ValidationEngine
from core.prompts import PromptManager
from core.reasoning_engine import (
    decide_intent_with_rules,
    decide_next_ticket_action,
    decide_next_delay_action,
)
from core.slot_manager import SlotManager

from nlp.parser import LLMParser
from adapters.ticket_adapter import TicketSearchAdapter
from adapters.delay_adapter import DelayPredictionAdapter
from adapters.disruptions_adapter import get_disruptions, is_disruption_query
from knowledge.kb import KnowledgeBase

DELAY_FAQ_PHRASES = {
    "delay repay", "compensation", "claim compensation", "how much compensation",
    "am i eligible", "get money back", "refund for delay", "delayed train refund"
}

OPEN_RETURN_PHRASES = {
    "open return", "open ticket", "flexible return", "no return date",
    "not sure when i'm coming back", "not sure when im coming back",
    "flexible", "no preference", "don't know when", "dont know when",
}


class ConversationController:

    YES_WORDS = {"yes", "y", "correct", "yeah", "yep", "sure", "ok", "okay"}
    NO_WORDS = {"no", "n", "wrong", "incorrect", "change", "edit", "not correct"}

    def __init__(self):
        self.state = ChatState()
        self.parser = LLMParser()
        self.validator = ValidationEngine()
        self.prompts = PromptManager()
        self.ticket_search = TicketSearchAdapter()
        self.delay_predictor = DelayPredictionAdapter()
        self.kb = KnowledgeBase()
        self.slot_manager = SlotManager()
        self.confirm_ticket = False
        self.confirm_delay = False
        self.pending_station_candidates = []

    def _set_pending(self, value: Optional[str]) -> None:
        self.state.pending_correction_slot = value

    def _get_pending(self) -> Optional[str]:
        return self.state.pending_correction_slot

    def _clear_pending(self) -> None:
        self.state.pending_correction_slot = None
        self.pending_station_candidates = []

    def apply_updates(self, target, data: Dict[str, Any]) -> None:
        clean = {
            key: value
            for key, value in data.items()
            if key not in {"station_ambiguity", "station_not_found"}
        }
        self.slot_manager.apply_updates(target, clean)

    def _reset(self) -> str:
        self.state.reset()
        self.confirm_ticket = False
        self.confirm_delay = False
        self.pending_station_candidates = []
        return "Conversation reset. How can I help you?"

    def _is_goodbye_or_done(self, text: str) -> bool:
        clean = text.lower().strip()
        if clean in {
            "bye", "goodbye", "thanks", "thank you", "thanks bye", "thank you bye",
            "done", "done over", "finished", "finish", "that's all", "that is all",
            "all good", "no thanks",
        }:
            return True
        return "bye" in clean or clean.startswith("thank")

    def _finish_conversation(self) -> str:
        self.state.current_task = None
        self.state.ticket = JourneyState()
        self.state.delay = DelayState()
        self.confirm_ticket = False
        self.confirm_delay = False
        self._clear_pending()
        return "You're welcome. Safe travels!"

    def _looks_like_slot_answer(self, text: str) -> bool:
        lower = text.lower().strip()
        if any(word in lower for word in [
            "tomorrow", "today", "monday", "tuesday", "wednesday", "thursday",
            "friday", "saturday", "sunday", "morning", "afternoon", "evening",
            "single", "return", "yes", "no", "after", "before", "am", "pm",
            "minutes", "mins", "hour", "open", "flexible"
        ]):
            return True
        if lower.replace(" ", "").isdigit():
            return True
        return False

    def _looks_like_journey_request(self, text: str) -> bool:
        lower = text.lower().strip()
        if " to " in lower and len(lower.split()) >= 3:
            return True
        starters = ["from ", "go to ", "travel to ", "i want to go", "get me to", "i need to go"]
        return any(s in lower for s in starters)

    def _is_delay_faq(self, text: str) -> bool:
        lower = text.lower().strip()
        return any(phrase in lower for phrase in DELAY_FAQ_PHRASES)

    def _is_open_return_phrase(self, text: str) -> bool:
        lower = text.lower().strip()
        return any(phrase in lower for phrase in OPEN_RETURN_PHRASES)

    def handle_user_input(self, text: str) -> str:
        clean = text.lower().strip()

        if clean in {"restart", "reset"}:
            return self._reset()

        if clean in {"hi", "hello", "hey", "hiya", "good morning", "good afternoon", "good evening"}:
            return (
                "Hi! I can help you find train tickets, check delay predictions, "
                "or answer general train travel questions."
            )

        if self._is_goodbye_or_done(text):
            return self._finish_conversation()

        if self.confirm_ticket:
            return self._confirm_ticket(text)

        if self.confirm_delay:
            return self._confirm_delay(text)

        pending = self._get_pending()
        if pending:
            return self._handle_pending(text, pending)

        if self.state.current_task is None and is_disruption_query(text):
            result = get_disruptions()
            return result["message"]

        if self.state.current_task is None:
            nlu = self.parser.understand(text)
            self.state.last_intent = nlu.intent
            self.state.last_confidence = nlu.intent_confidence
            self.state.last_nlu_source = nlu.source

            flow = decide_intent_with_rules(nlu.intent)

            if flow == "ticket_flow":
                self.state.current_task = "ticket"

            elif flow == "delay_flow":
                if self._is_delay_faq(text):
                    answer = self.kb.search(text)
                    if answer:
                        return answer
                self.state.current_task = "delay"

            else:
                if "disruption" in (nlu.intent or "").lower():
                    result = get_disruptions()
                    return result["message"]

                if self._looks_like_journey_request(text):
                    self.state.current_task = "ticket"
                else:
                    answer = self.kb.search(text)
                    return answer if answer else self.prompts.fallback()

        if self.state.current_task == "ticket":
            kb_answer = self.kb.search(text)
            if kb_answer and not self._looks_like_slot_answer(text):
                return kb_answer
            return self._ticket_flow(text)

        if self.state.current_task == "delay":
            kb_answer = self.kb.search(text)
            if kb_answer and not self._looks_like_slot_answer(text):
                return kb_answer
            return self._delay_flow(text)

        answer = self.kb.search(text)
        return answer if answer else self.prompts.fallback()

    def _handle_station_meta(self, extracted: Dict[str, Any], task: str) -> Optional[str]:
        if extracted.get("station_not_found"):
            bad = extracted["station_not_found"]
            slot_label = bad.get("slot", "station").replace("_", " ")
            return (
                f"Sorry, I could not find a station called '{bad['raw_text']}' "
                f"for {slot_label}. Please try the full station name."
            )

        if extracted.get("station_ambiguity"):
            amb = extracted["station_ambiguity"]
            slot = amb["slot"]
            self._set_pending(f"choose_station:{task}:{slot}")
            self.pending_station_candidates = amb["candidates"]
            options = "\n".join(
                f"{index + 1}. {station}"
                for index, station in enumerate(self.pending_station_candidates)
            )
            return (
                f"I found several matching stations for '{amb['raw_text']}'.\n\n"
                f"{options}\n\n"
                "Reply with the number or the full station name."
            )

        return None

    def _resolve_station_choice(self, text: str, pending: str) -> str:
        _, task, slot = pending.split(":", 2)
        clean = text.strip()

        if clean.isdigit():
            index = int(clean) - 1
            if 0 <= index < len(self.pending_station_candidates):
                selected = self.pending_station_candidates[index]
                self._assign_station_slot(task, slot, selected)
                self._clear_pending()
                return self._next_ticket_response() if task == "ticket" else self._next_delay_response()

        match = self.parser.match_station_with_status(clean)
        if match.status == "exact":
            self._assign_station_slot(task, slot, match.station)
            self._clear_pending()
            return self._next_ticket_response() if task == "ticket" else self._next_delay_response()

        if match.status == "ambiguous":
            self.pending_station_candidates = [candidate.station for candidate in match.candidates]
            options = "\n".join(
                f"{index + 1}. {station}"
                for index, station in enumerate(self.pending_station_candidates)
            )
            return f"I found several matching stations. Which one do you mean?\n\n{options}"

        return "Sorry, I could not find that station. Please enter the full station name."

    def _assign_station_slot(self, task: str, slot: str, station: str) -> None:
        if task == "ticket":
            setattr(self.state.ticket, slot, station)
        elif task == "delay":
            setattr(self.state.delay, slot, station)

    def _pending_station_options_prompt(self) -> str:
        options = "\n".join(
            f"{index + 1}. {station}"
            for index, station in enumerate(self.pending_station_candidates)
        )
        return f"I found several matching stations. Which one do you mean?\n\n{options}"

    def _ticket_flow(self, text: str) -> str:
        # Intercept open return before the parser tries to match it as a station name
        if self._is_open_return_phrase(text):
            if self.state.ticket.journey_type in ("return", None):
                self.state.ticket.journey_type = "return"
                self.state.ticket.return_date = "open"
                self.state.ticket.return_time_pref = None
                return self._next_ticket_response()

        if self.state.ticket.from_station or self.state.ticket.to_station:
            clear = self.slot_manager.detect_corrections(text, task="ticket")
            self.slot_manager.clear_slots(self.state.ticket, clear)

        extracted = self.parser.extract(text, self.state.ticket.to_dict(), task="ticket")
        meta = self._handle_station_meta(extracted, task="ticket")
        if meta:
            return meta

        self.apply_updates(self.state.ticket, extracted)
        return self._next_ticket_response()

    def _next_ticket_response(self) -> str:
        errors = self.validator.validate_journey(self.state.ticket)
        if errors:
            return self.prompts.validation_errors(errors)

        missing = self.state.ticket.missing_slots()
        action = decide_next_ticket_action(missing)

        if action == "ticket_complete":
            self.confirm_ticket = True
            self._clear_pending()
            return self.prompts.confirm_summary(self.state.ticket.summary())

        if missing:
            slot = missing[0]
            self._set_pending(f"ticket:{slot}")
            return self.prompts.ask_for(slot, context=self.state.ticket.to_dict())

        return self.prompts.fallback()

    def _confirm_ticket(self, text: str) -> str:
        answer = text.lower().strip()
        first_word = answer.split()[0] if answer.split() else answer

        if answer in self.YES_WORDS or first_word in self.YES_WORDS:
            result = self.ticket_search.search_cheapest(self.state.ticket.to_dict())
            self.confirm_ticket = False
            self.state.current_task = None
            self.state.ticket = JourneyState()
            self._clear_pending()
            return f"Great — your journey details are complete.\n\n{result['message']}"

        if answer in self.NO_WORDS or first_word in self.NO_WORDS:
            self.confirm_ticket = False
            self._set_pending("ticket_change")
            return (
                "No problem. What needs changing?\n"
                "You can say: destination, departure station, date, return date, journey type, or time."
            )

        target = self._classify_ticket_correction_target(text)
        if target:
            self.confirm_ticket = False
            updated = self._update_specific_ticket_slot(target, text)
            if updated:
                self._clear_pending()
                self.state.current_task = "ticket"
                return self._next_ticket_response()
            self._set_pending(f"ticket:{target}")
            return self._ask_for_ticket_correction(target)

        return "Please answer yes or no. If something is wrong, say what to change."

    def _has_explicit_ticket_slot_label(self, text: str) -> bool:
        lower = text.lower().strip()
        labels = [
            "return time", "coming back time", "come back time", "back time", "inbound time",
            "return date", "coming back date", "come back date", "back date",
            "departure time", "depart time", "outbound time",
            "departure date", "depart date", "travel date",
            "destination", "to station", "from station", "departure station", "origin",
            "journey type", "ticket type",
        ]
        return any(label in lower for label in labels)

    def _classify_ticket_correction_target(self, text: str) -> Optional[str]:
        lower = text.lower().strip()
        exact = {
            "return time": "return_time_pref", "coming back time": "return_time_pref",
            "come back time": "return_time_pref", "back time": "return_time_pref",
            "time": "depart_time_pref", "depart time": "depart_time_pref",
            "departure time": "depart_time_pref", "outbound time": "depart_time_pref",
            "date": "depart_date", "day": "depart_date",
            "depart date": "depart_date", "departure date": "depart_date",
            "return date": "return_date", "coming back date": "return_date",
            "come back date": "return_date", "back date": "return_date",
            "destination": "to_station", "to station": "to_station",
            "arrival station": "to_station",
            "departure station": "from_station", "from station": "from_station",
            "origin": "from_station",
            "journey type": "journey_type", "ticket type": "journey_type",
            "single": "journey_type", "return": "journey_type",
        }
        if lower in exact:
            return exact[lower]

        keywords = {
            "return_time_pref": ["return time", "coming back time", "come back time", "back time", "inbound time"],
            "return_date": ["return date", "coming back date", "come back date", "back date"],
            "depart_time_pref": ["depart time", "departure time", "outbound time", "time", "leave", "leaving", "after", "before", "morning", "afternoon", "evening"],
            "depart_date": ["depart date", "departure date", "travel date", "date", "day", "tomorrow", "next"],
            "to_station": ["destination", "arrival", "to station", "where to"],
            "from_station": ["from station", "departure station", "origin"],
            "journey_type": ["single", "return journey", "one way", "ticket type"],
        }
        for slot, words in keywords.items():
            if any(word in lower for word in words):
                return slot
        return None

    def _ask_for_ticket_correction(self, slot: str) -> str:
        questions = {
            "from_station": "Sure — what departure station should I use?",
            "to_station": "Sure — what destination station should I use?",
            "depart_date": "Sure — what date are you travelling? You can say 'tomorrow' or '15 July'.",
            "depart_time_pref": "Sure — what departure time do you prefer? For example: 'morning', 'before 10am', or 'after 2pm'.",
            "return_date": "Sure — what date are you coming back? You can also say 'open return' if the date is flexible.",
            "return_time_pref": "Sure — what return time do you prefer? For example: 'after 2pm'.",
            "journey_type": "Sure — is this a single or return journey?",
        }
        return questions.get(slot, "Sure — what should I change it to?")

    def _update_specific_ticket_slot(self, slot: str, text: str) -> bool:
        lower = text.lower().strip()

        # Handle open return for both return_date and journey_type slots
        if slot in {"return_date", "journey_type"} and self._is_open_return_phrase(text):
            self.state.ticket.journey_type = "return"
            self.state.ticket.return_date = "open"
            self.state.ticket.return_time_pref = None
            return True

        if slot in {"from_station", "to_station"}:
            match = self.parser.match_station_with_status(text)
            if match.status == "exact":
                setattr(self.state.ticket, slot, match.station)
                return True
            if match.status == "ambiguous":
                self._set_pending(f"choose_station:ticket:{slot}")
                self.pending_station_candidates = [candidate.station for candidate in match.candidates]
                return False
            return False

        extracted = self.parser.extract(text, self.state.ticket.to_dict(), task="ticket")

        if slot == "journey_type":
            if "return" in lower or "round" in lower:
                self.state.ticket.journey_type = "return"
                return True
            if "single" in lower or "one way" in lower or "one-way" in lower:
                self.state.ticket.journey_type = "single"
                self.state.ticket.return_date = None
                self.state.ticket.return_time_pref = None
                return True
            return False

        if extracted.get(slot) not in (None, "", []):
            setattr(self.state.ticket, slot, extracted[slot])
            if slot == "depart_date" and extracted.get("depart_time_pref"):
                self.state.ticket.depart_time_pref = extracted["depart_time_pref"]
            if slot == "depart_time_pref" and extracted.get("depart_date") and not self.state.ticket.depart_date:
                self.state.ticket.depart_date = extracted["depart_date"]
            if slot == "return_date":
                if extracted.get("return_time_pref"):
                    self.state.ticket.return_time_pref = extracted["return_time_pref"]
                elif extracted.get("depart_time_pref"):
                    self.state.ticket.return_time_pref = extracted["depart_time_pref"]
            if slot == "return_time_pref" and extracted.get("return_date") and not self.state.ticket.return_date:
                self.state.ticket.return_date = extracted["return_date"]
            return True

        if slot == "return_date" and extracted.get("depart_date"):
            self.state.ticket.return_date = extracted["depart_date"]
            return True
        if slot == "return_time_pref" and extracted.get("depart_time_pref"):
            self.state.ticket.return_time_pref = extracted["depart_time_pref"]
            return True
        if slot == "depart_time_pref" and extracted.get("return_time_pref"):
            self.state.ticket.depart_time_pref = extracted["return_time_pref"]
            return True
        if slot == "depart_date" and extracted.get("return_date"):
            self.state.ticket.depart_date = extracted["return_date"]
            return True

        return False

    def _retry_ticket_slot_prompt(self, slot: str) -> str:
        prompts = {
            "from_station": "I still need the departure station. Please enter the full station name.",
            "to_station": "I still need the destination station. Please enter the full station name.",
            "journey_type": "I still need to know whether this is single or return.",
            "depart_date": "I still need the travel date. For example: 'tomorrow' or '15 July'.",
            "depart_time_pref": "I still need the departure time. For example: 'morning', 'before 10am', or 'after 2pm'.",
            "return_date": "I still need the return date. For example: '30 July'. You can also say 'open return' if the date is flexible.",
            "return_time_pref": "I still need the return time. For example: 'after 2pm' or 'no preference'.",
        }
        return prompts.get(slot, "I still need that detail.")

    def _delay_flow(self, text: str) -> str:
        clear = self.slot_manager.detect_corrections(text, task="delay")
        self.slot_manager.clear_slots(self.state.delay, clear)

        extracted = self.parser.extract(text, self.state.delay.to_dict(), task="delay")
        meta = self._handle_station_meta(extracted, task="delay")
        if meta:
            return meta

        extracted.pop("train_id", None)
        self.apply_updates(self.state.delay, extracted)
        return self._next_delay_response()

    def _next_delay_response(self) -> str:
        errors = self.validator.validate_delay(self.state.delay)
        if errors:
            return self.prompts.validation_errors(errors)

        missing = self.state.delay.missing_slots()
        action = decide_next_delay_action(missing)

        if action == "delay_complete":
            self.confirm_delay = True
            self._clear_pending()
            return (
                "Thanks. Here is the delay information I collected:\n\n"
                f"{self.state.delay.summary()}\n\n"
                "Is this correct? (yes/no)"
            )

        if missing:
            slot = missing[0]
            self._set_pending(f"delay:{slot}")
            return self.prompts.ask_for(slot, context=self.state.delay.to_dict())

        return self.prompts.fallback()

    def _confirm_delay(self, text: str) -> str:
        answer = text.lower().strip()
        first_word = answer.split()[0] if answer.split() else answer

        if answer in self.YES_WORDS or first_word in self.YES_WORDS:
            result = self.delay_predictor.predict_arrival(self.state.delay.to_dict())
            self.confirm_delay = False
            self.state.current_task = None
            self.state.delay = DelayState()
            self._clear_pending()
            return f"Great — the delay details are complete.\n\n{result['message']}"

        if answer in self.NO_WORDS or first_word in self.NO_WORDS:
            self.confirm_delay = False
            self._set_pending("delay_change")
            return "No problem. What needs changing? You can say: current station, delay, or destination."

        target = self._classify_delay_correction_target(text)
        if target:
            self.confirm_delay = False
            self._set_pending(f"delay:{target}")
            return self._ask_for_delay_correction(target)

        return "Please answer yes or no. If something is wrong, say what to change."

    def _classify_delay_correction_target(self, text: str) -> Optional[str]:
        lower = text.lower().strip()
        if any(word in lower for word in ["delay", "late", "minutes", "mins"]):
            return "delay_minutes"
        if any(word in lower for word in ["current", "currently", "now at", "reached", "where now"]):
            return "current_station"
        if any(word in lower for word in ["destination", "going to", "to station", "arrival station"]):
            return "destination"
        return None

    def _ask_for_delay_correction(self, slot: str) -> str:
        questions = {
            "current_station": "Sure — which station has the train currently reached?",
            "delay_minutes": "Sure — how many minutes is the train delayed?",
            "destination": "Sure — what is your destination station?",
        }
        return questions.get(slot, "Sure — what should I change it to?")

    def _update_specific_delay_slot(self, slot: str, text: str) -> bool:
        clean = text.strip()
        lower = clean.lower()

        if slot in {"current_station", "destination"}:
            extracted = self.parser.extract(clean, self.state.delay.to_dict(), task="delay")

            if extracted.get(slot) not in (None, "", []):
                extracted.pop("train_id", None)
                meta = self._handle_station_meta(extracted, task="delay")
                self.apply_updates(self.state.delay, extracted)
                if meta:
                    return False
                return True

            if extracted.get("station_ambiguity") and extracted["station_ambiguity"].get("slot") == slot:
                self._handle_station_meta(extracted, task="delay")
                return False

            match = self.parser.match_station_with_status(clean)
            if match.status == "exact":
                setattr(self.state.delay, slot, match.station)
                return True
            if match.status == "ambiguous":
                self._set_pending(f"choose_station:delay:{slot}")
                self.pending_station_candidates = [candidate.station for candidate in match.candidates]
                return False
            return False

        if slot == "delay_minutes":
            extracted = self.parser.extract(clean, self.state.delay.to_dict(), task="delay")
            extracted.pop("train_id", None)
            if extracted.get("delay_minutes") not in (None, "", []):
                self.apply_updates(self.state.delay, extracted)
                return True
            if lower.isdigit():
                self.state.delay.delay_minutes = int(lower)
                return True
            return False

        return False

    def _retry_delay_slot_prompt(self, slot: str) -> str:
        prompts = {
            "current_station": "I still need the current station. Please enter the full station name.",
            "delay_minutes": "I still need the delay in minutes. For example: '10 minutes'.",
            "destination": "I still need the destination station. Please enter the full station name.",
        }
        return prompts.get(slot, "I still need that detail.")

    def _handle_pending(self, text: str, pending: str) -> str:
        if pending.startswith("choose_station:"):
            return self._resolve_station_choice(text, pending)

        if pending == "ticket_change":
            target = self._classify_ticket_correction_target(text)
            if target:
                self._set_pending(f"ticket:{target}")
                return self._ask_for_ticket_correction(target)
            self._clear_pending()
            self.state.current_task = "ticket"
            return self._ticket_flow(text)

        if pending == "delay_change":
            target = self._classify_delay_correction_target(text)
            if target:
                self._set_pending(f"delay:{target}")
                return self._ask_for_delay_correction(target)
            self._clear_pending()
            self.state.current_task = "delay"
            return self._delay_flow(text)

        if pending.startswith("ticket:"):
            slot = pending.split(":", 1)[1]

            explicit_target = self._classify_ticket_correction_target(text)
            if explicit_target and explicit_target != slot and self._has_explicit_ticket_slot_label(text):
                slot = explicit_target

            updated = self._update_specific_ticket_slot(slot, text)
            if not updated:
                if self._get_pending() and self._get_pending().startswith("choose_station:"):
                    return self._pending_station_options_prompt()
                return self._retry_ticket_slot_prompt(slot)
            self._clear_pending()
            self.state.current_task = "ticket"
            return self._next_ticket_response()

        if pending.startswith("delay:"):
            slot = pending.split(":", 1)[1]
            updated = self._update_specific_delay_slot(slot, text)
            if not updated:
                if self._get_pending() and self._get_pending().startswith("choose_station:"):
                    return self._pending_station_options_prompt()
                return self._retry_delay_slot_prompt(slot)
            self._clear_pending()
            self.state.current_task = "delay"
            return self._next_delay_response()

        self._clear_pending()
        return self.prompts.fallback()

    def run(self):
        print(self.prompts.greeting())
        while True:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in {"quit", "exit"}:
                print("Bot: Goodbye.")
                break
            print(f"\nBot: {self.handle_user_input(user_input)}")