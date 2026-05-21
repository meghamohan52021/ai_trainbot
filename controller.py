from typing import Any, Dict, Optional

from state import ChatState, JourneyState, DelayState
from parser import LLMParser
from validation import ValidationEngine
from prompts import PromptManager
from ticket_adapter import TicketSearchAdapter
from delay_adapter import DelayPredictionAdapter
from kb import KnowledgeBase
from reasoning_engine import (
    decide_intent_with_rules,
    decide_next_ticket_action,
    decide_next_delay_action,
)
from slot_manager import SlotManager


class ConversationController:
    #This class manages the conversation state and flow, integrating all components together

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

        if not hasattr(self.state, "pending_correction_slot"):
            setattr(self.state, "pending_correction_slot", None)

    # State helpers
    def _set_pending(self, slot_name: Optional[str]) -> None:
        setattr(self.state, "pending_correction_slot", slot_name)

    def _get_pending(self) -> Optional[str]:
        return getattr(self.state, "pending_correction_slot", None)

    def _clear_pending(self) -> None:
        self._set_pending(None)
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
        self._clear_pending()
        return "Conversation reset. How can I help you?"
    
    def _is_goodbye_or_done(self, text: str) -> bool:
        clean = text.lower().strip()

        goodbye_phrases = {
            "bye",
            "goodbye",
            "thanks",
            "thank you",
            "thanks bye",
            "thank you bye",
            "done",
            "done over",
            "finished",
            "finish",
            "that's all",
            "that is all",
            "all good",
            "no thanks",
        }

        if clean in goodbye_phrases:
            return True

        if "bye" in clean:
            return True

        if clean.startswith("thank"):
            return True

        return False


    def _finish_conversation(self) -> str:
        self.state.current_task = None
        self.state.ticket = JourneyState()
        self.state.delay = DelayState()
        self.confirm_ticket = False
        self.confirm_delay = False
        self._clear_pending()
        return "You're welcome. Safe travels!"


    # Main entry point
    def handle_user_input(self, text: str) -> str:
        clean = text.lower().strip()


        if clean in {"restart", "reset"}:
            return self._reset()
        
        if self._is_goodbye_or_done(text):
            return self._finish_conversation()

        pending = self._get_pending()
        if pending:
            return self._handle_pending_correction(text, pending)

        if self.confirm_ticket:
            return self._confirm_ticket(text)

        if self.confirm_delay:
            return self._confirm_delay(text)

        if self.state.current_task is None:
            nlu = self.parser.understand(text)
            self.state.last_intent = nlu.intent
            self.state.last_confidence = nlu.intent_confidence
            self.state.last_nlu_source = nlu.source

            flow = decide_intent_with_rules(nlu.intent)
            if flow == "ticket_flow":
                self.state.current_task = "ticket"
            elif flow == "delay_flow":
                self.state.current_task = "delay"
            else:
                ans = self.kb.search(text)
                return ans if ans else self.prompts.fallback()

        if self.state.current_task == "ticket":
            return self._ticket_flow(text)

        if self.state.current_task == "delay":
            return self._delay_flow(text)

        ans = self.kb.search(text)
        return ans if ans else self.prompts.fallback()


    #Station ambiguity / not found handlers
    def _handle_station_meta(self, extracted: Dict[str, Any], task: str) -> Optional[str]:
        if extracted.get("station_not_found"):
            bad = extracted["station_not_found"]
            slot_label = bad.get("slot", "station").replace("_", " ")
            return (
                f"Sorry, I could not find a station called '{bad['raw_text']}' "
                f"in the station data for {slot_label}. Please try the full station name."
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
            slot_label = slot.replace("_", " ")
            return (
                f"I found several matching stations for '{amb['raw_text']}'. "
                f"Which {slot_label} do you mean?\n\n"
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
            self.pending_station_candidates = [c.station for c in match.candidates]
            options = "\n".join(
                f"{index + 1}. {station}"
                for index, station in enumerate(self.pending_station_candidates)
            )
            return (
                f"I found several matching stations for '{clean}'. Which one do you mean?\n\n"
                f"{options}\n\n"
                "Reply with the number or the full station name."
            )

        return (
            f"Sorry, I could not find a station called '{clean}' in the station data. "
            "Please try the full station name."
        )

    def _assign_station_slot(self, task: str, slot: str, station: str) -> None:
        if task == "ticket":
            setattr(self.state.ticket, slot, station)
        elif task == "delay":
            setattr(self.state.delay, slot, station)


    #Ticket flow
    def _ticket_flow(self, text: str) -> str:
        clear = self.slot_manager.detect_corrections(text, task="ticket")
        self.slot_manager.clear_slots(self.state.ticket, clear)

        extracted = self.parser.extract(text, self.state.ticket.to_dict(), task="ticket")
        meta_response = self._handle_station_meta(extracted, task="ticket")
        if meta_response:
            return meta_response

        self.apply_updates(self.state.ticket, extracted)
        return self._next_ticket_response()

    def _next_ticket_response(self) -> str:
        errs = self.validator.validate_journey(self.state.ticket)
        if errs:
            return self.prompts.validation_errors(errs)

        missing = self.state.ticket.missing_slots()
        action = decide_next_ticket_action(missing)

        if action == "ticket_complete":
            self.confirm_ticket = True
            return self.prompts.confirm_summary(self.state.ticket.summary())

        return action

    def _confirm_ticket(self, text: str) -> str:
        ans = text.lower().strip()

        if ans in self.YES_WORDS:
            result = self.ticket_search.search_cheapest(self.state.ticket.to_dict())
            self.confirm_ticket = False
            self.state.current_task = None
            self.state.ticket = JourneyState()
            self._clear_pending()
            return f"Great - your journey details are complete.\n\n{result['message']}"

        if ans in self.NO_WORDS:
            self.confirm_ticket = False
            self._set_pending("ticket_change")
            return (
                "No problem. What needs changing?\n"
                "You can say: destination, departure station, date, return date, journey type, or time."
            )

        target = self._classify_ticket_correction_target(text)
        if target:
            self.confirm_ticket = False
            self._set_pending(target)
            return self._ask_for_ticket_correction(target)

        extracted = self.parser.extract(text, self.state.ticket.to_dict(), task="ticket")
        meta_response = self._handle_station_meta(extracted, task="ticket")
        if meta_response:
            self.confirm_ticket = False
            return meta_response

        changed = self._apply_ticket_correction_values(extracted)
        if changed:
            self.confirm_ticket = False
            self._clear_pending()
            return self._next_ticket_response()

        return (
            "Please answer yes or no. If something is wrong, you can also say what to change, "
            "for example: 'I want to depart after 2pm'."
        )

    # Pending correction handling
    def _handle_pending_correction(self, text: str, pending: str) -> str:
        if pending.startswith("choose_station:"):
            return self._resolve_station_choice(text, pending)

        if pending == "ticket_change":
            lower = text.lower().strip()
            if lower in {"everything", "all", "start again", "start over", "restart journey", "reset journey"}:
                self.state.ticket = type(self.state.ticket)()
                self.state.current_task = "ticket"
                self._clear_pending()
                self.confirm_ticket = False
                return "Okay, let’s start the journey again. Where are you travelling from and to?"

            target = self._classify_ticket_correction_target(text)
            if target:
                self._set_pending(target)
                return self._ask_for_ticket_correction(target)

            extracted = self.parser.extract(text, self.state.ticket.to_dict(), task="ticket")
            meta_response = self._handle_station_meta(extracted, task="ticket")
            if meta_response:
                return meta_response

            changed = self._apply_ticket_correction_values(extracted)
            if changed:
                self._clear_pending()
                self.state.current_task = "ticket"
                return self._next_ticket_response()

            return (
                "I did not catch which part to change. Please say one of: "
                "destination, departure station, date, return date, journey type, or time."
            )

        if pending in {
            "from_station", "to_station", "depart_date", "depart_time_pref",
            "return_date", "return_time_pref", "journey_type",
        }:
            updated = self._update_specific_ticket_slot(pending, text)
            if not updated:
                return self._retry_ticket_correction_prompt(pending)
            self._clear_pending()
            self.state.current_task = "ticket"
            return self._next_ticket_response()

        if pending == "delay_change":
            target = self._classify_delay_correction_target(text)
            if target:
                self._set_pending(target)
                return self._ask_for_delay_correction(target)

            extracted = self.parser.extract(text, self.state.delay.to_dict(), task="delay")
            meta_response = self._handle_station_meta(extracted, task="delay")
            if meta_response:
                return meta_response

            changed = self._apply_delay_correction_values(extracted)
            if changed:
                self._clear_pending()
                self.state.current_task = "delay"
                return self._next_delay_response()

            return "I did not catch which delay detail to change. Please say: train, current station, delay, or destination."

        if pending in {"train_id", "current_station", "delay_minutes", "destination"}:
            updated = self._update_specific_delay_slot(pending, text)
            if not updated:
                return self._retry_delay_correction_prompt(pending)
            self._clear_pending()
            self.state.current_task = "delay"
            return self._next_delay_response()

        self._clear_pending()
        return self.prompts.fallback()

    def _classify_ticket_correction_target(self, text: str) -> Optional[str]:
        lower = text.lower().strip()

        
        exact_slot_words = {
            "time": "depart_time_pref",
            "depart time": "depart_time_pref",
            "departure time": "depart_time_pref",
            "preferred time": "depart_time_pref",
            "date": "depart_date",
            "day": "depart_date",
            "depart date": "depart_date",
            "departure date": "depart_date",
            "return date": "return_date",
            "coming back date": "return_date",
            "destination": "to_station",
            "to station": "to_station",
            "arrival station": "to_station",
            "departure station": "from_station",
            "from station": "from_station",
            "origin": "from_station",
            "journey type": "journey_type",
            "ticket type": "journey_type",
            "single": "journey_type",
            "return": "journey_type",
        }
        if lower in exact_slot_words:
            return exact_slot_words[lower]

        slot_keywords = {
            "depart_time_pref": ["time", "depart", "departure time", "preferred time", "leave", "leaving", "after", "before", "morning", "afternoon", "evening"],
            "depart_date": ["date", "day", "depart date", "departure date", "travel date", "tomorrow", "next"],
            "return_date": ["return date", "coming back", "come back", "back date"],
            "to_station": ["destination", "arrival station", "to station", "where to"],
            "from_station": ["from station", "departure station", "origin"],
            "journey_type": ["single", "return", "one way", "journey type", "ticket type"],
        }

        best_slot = None
        best_score = 0
        for slot, keywords in slot_keywords.items():
            score = sum(1 for kw in keywords if kw in lower)
            if score > best_score:
                best_score = score
                best_slot = slot

        if best_slot:
            return best_slot

        #This catches full correction sentences like
        #"change destination to Cambridge" or "I want to depart after 2pm"
        extracted = self.parser.extract(text, self.state.ticket.to_dict(), task="ticket")
        for slot in ["depart_time_pref", "return_time_pref", "depart_date", "return_date", "from_station", "to_station", "journey_type"]:
            if extracted.get(slot) not in (None, "", []):
                return slot

        return None

    def _ask_for_ticket_correction(self, slot: str) -> str:
        questions = {
            "from_station": "Sure — what departure station should I use?",
            "to_station": "Sure — what destination station should I use?",
            "depart_date": "Sure — what date are you travelling? You can say 'tomorrow' or '15 July'.",
            "depart_time_pref": "Sure — what departure time do you prefer? For example: 'morning', 'before 10am', or 'after 2pm'.",
            "return_date": "Sure — what date are you coming back?",
            "return_time_pref": "Sure — what return time do you prefer? For example: 'after 2pm'.",
            "journey_type": "Sure — is this a single or return journey?",
        }
        return questions.get(slot, "Sure — what should I change it to?")

    def _retry_ticket_correction_prompt(self, slot: str) -> str:
        retries = {
            "from_station": "I still need the departure station. Please enter the full station name.",
            "to_station": "I still need the destination station. Please enter the full station name.",
            "depart_date": "I still need the travel date. For example: 'tomorrow' or '2026-07-15'.",
            "depart_time_pref": "I still need the departure time preference. For example: 'morning', 'before 10am', or 'after 2pm'.",
            "return_date": "I still need the return date. For example: 'the day after tomorrow'.",
            "return_time_pref": "I still need the return time preference. For example: 'after 2pm'.",
            "journey_type": "I still need to know whether this is single or return.",
        }
        return retries.get(slot, "I still need the new value.")

    def _update_specific_ticket_slot(self, slot: str, text: str) -> bool:
        lower = text.lower().strip()

        #Station slots: station matching and ambiguity handling are valid here
        if slot in {"from_station", "to_station"}:
            match = self.parser.match_station_with_status(text)
            if match.status == "exact":
                setattr(self.state.ticket, slot, match.station)
                return True
            if match.status == "ambiguous":
                self._set_pending(f"choose_station:ticket:{slot}")
                self.pending_station_candidates = [c.station for c in match.candidates]
                return False
            return False

        #Non-station slots: ignore station_not_found/station_ambiguity completely
        #This prevents "tomorrow" or "after 2pm" from becoming station errors
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

        if extracted.get(slot) not in (None, "", []):
            setattr(self.state.ticket, slot, extracted[slot])
            return True

        if slot == "return_date" and extracted.get("depart_date"):
            self.state.ticket.return_date = extracted["depart_date"]
            return True

        if slot == "return_time_pref" and extracted.get("depart_time_pref"):
            self.state.ticket.return_time_pref = extracted["depart_time_pref"]
            return True

        return False

    def _apply_ticket_correction_values(self, extracted: Dict[str, Any]) -> bool:
        changed = False
        for slot in ["from_station", "to_station", "journey_type", "depart_date", "depart_time_pref", "return_date", "return_time_pref"]:
            value = extracted.get(slot)
            if value not in (None, "", []):
                setattr(self.state.ticket, slot, value)
                changed = True

        if self.state.ticket.journey_type == "single":
            self.state.ticket.return_date = None
            self.state.ticket.return_time_pref = None

        return changed

    
    #Delay flow
    def _delay_flow(self, text: str) -> str:
        clear = self.slot_manager.detect_corrections(text, task="delay")
        self.slot_manager.clear_slots(self.state.delay, clear)

        extracted = self.parser.extract(text, self.state.delay.to_dict(), task="delay")
        meta_response = self._handle_station_meta(extracted, task="delay")
        if meta_response:
            return meta_response

        self.apply_updates(self.state.delay, extracted)
        return self._next_delay_response()

    def _next_delay_response(self) -> str:
        errs = self.validator.validate_delay(self.state.delay)
        if errs:
            return self.prompts.validation_errors(errs)

        missing = self.state.delay.missing_slots()
        action = decide_next_delay_action(missing)

        if action == "delay_complete":
            self.confirm_delay = True
            return (
                "Thanks. Here is the delay information I collected:\n\n"
                f"{self.state.delay.summary()}\n\n"
                "Is this correct? (yes/no)"
            )

        return action

    def _confirm_delay(self, text: str) -> str:
        ans = text.lower().strip()

        if ans in self.YES_WORDS:
            result = self.delay_predictor.predict_arrival(self.state.delay.to_dict())
            self.confirm_delay = False
            self.state.current_task = None
            self.state.delay = DelayState()
            self._clear_pending()
            return f"Great - the delay details are complete.\n\n{result['message']}"

        if ans in self.NO_WORDS:
            self.confirm_delay = False
            self._set_pending("delay_change")
            return "No problem. What needs changing?\nYou can say: train, current station, delay, or destination."

        target = self._classify_delay_correction_target(text)
        if target:
            self.confirm_delay = False
            self._set_pending(target)
            return self._ask_for_delay_correction(target)

        extracted = self.parser.extract(text, self.state.delay.to_dict(), task="delay")
        meta_response = self._handle_station_meta(extracted, task="delay")
        if meta_response:
            self.confirm_delay = False
            return meta_response

        changed = self._apply_delay_correction_values(extracted)
        if changed:
            self.confirm_delay = False
            self._clear_pending()
            return self._next_delay_response()

        return "Please answer yes or no. If something is wrong, you can also say what to change."

    def _classify_delay_correction_target(self, text: str) -> Optional[str]:
        lower = text.lower().strip()
        extracted = self.parser.extract(text, self.state.delay.to_dict(), task="delay")

        for slot in ["delay_minutes", "current_station", "destination", "train_id"]:
            if extracted.get(slot) not in (None, "", []):
                return slot

        slot_keywords = {
            "delay_minutes": ["delay", "late", "minutes", "mins", "time late"],
            "current_station": ["current station", "currently", "now at", "at station", "where now"],
            "destination": ["destination", "going to", "to station", "arrival station"],
            "train_id": ["train", "service", "train id", "service id"],
        }
        best_slot = None
        best_score = 0
        for slot, keywords in slot_keywords.items():
            score = sum(1 for kw in keywords if kw in lower)
            if score > best_score:
                best_score = score
                best_slot = slot
        return best_slot

    def _ask_for_delay_correction(self, slot: str) -> str:
        questions = {
            "train_id": "Sure — which train or service are you on? For example: 1W67.",
            "current_station": "Sure — which station has the train currently reached?",
            "delay_minutes": "Sure — how many minutes is the train delayed? You can say '15 minutes' or 'fifteen minutes'.",
            "destination": "Sure — what is your destination station?",
        }
        return questions.get(slot, "Sure — what should I change it to?")

    def _retry_delay_correction_prompt(self, slot: str) -> str:
        retries = {
            "train_id": "I still need the train or service ID. For example: 1W67.",
            "current_station": "I still need the current station. Please enter the full station name.",
            "delay_minutes": "I still need the delay in minutes. For example: 'fifteen minutes'.",
            "destination": "I still need the destination station. Please enter the full station name.",
        }
        return retries.get(slot, "I still need the new value.")

    def _update_specific_delay_slot(self, slot: str, text: str) -> bool:
        extracted = self.parser.extract(text, self.state.delay.to_dict(), task="delay")
        meta_response = self._handle_station_meta(extracted, task="delay")
        if meta_response:
            return False

        if slot in {"current_station", "destination"}:
            match = self.parser.match_station_with_status(text)
            if match.status == "exact":
                setattr(self.state.delay, slot, match.station)
                return True
            if match.status == "ambiguous":
                self._set_pending(f"choose_station:delay:{slot}")
                self.pending_station_candidates = [c.station for c in match.candidates]
                return False
            return False

        if extracted.get(slot) not in (None, "", []):
            setattr(self.state.delay, slot, extracted[slot])
            return True

        return False

    def _apply_delay_correction_values(self, extracted: Dict[str, Any]) -> bool:
        changed = False
        for slot in ["train_id", "current_station", "delay_minutes", "destination"]:
            value = extracted.get(slot)
            if value not in (None, "", []):
                setattr(self.state.delay, slot, value)
                changed = True
        return changed

    
    # CLI 
    def run(self):
        print(self.prompts.greeting())
        while True:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in {"quit", "exit"}:
                print("Bot: Goodbye.")
                break
            print(f"\nBot: {self.handle_user_input(user_input)}")
