from state import ChatState
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


class ConversationController:
    def __init__(self):
        self.state = ChatState()
        self.parser = LLMParser()
        self.validator = ValidationEngine()
        self.prompts = PromptManager()
        self.ticket_search = TicketSearchAdapter()
        self.delay_predictor = DelayPredictionAdapter()
        self.kb = KnowledgeBase()
        self.confirm_ticket = False
        self.confirm_delay = False

    def apply_updates(self, target, data: dict):
        for key, val in data.items():
            if hasattr(target, key) and val not in (None, "", []):
                setattr(target, key, val)

    def handle_user_input(self, text: str) -> str:
        if text.lower().strip() in {"restart", "reset"}:
            self.state.reset()
            self.confirm_ticket = False
            self.confirm_delay = False
            return "Conversation reset. How can I help you?"

        if self.confirm_ticket:
            return self._confirm_ticket(text)

        if self.confirm_delay:
            return self._confirm_delay(text)

        if self.state.current_task is None:
            intent = self.parser.detect_intent(text)
            flow = decide_intent_with_rules(intent)
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

    def _ticket_flow(self, text: str) -> str:
        extracted = self.parser.extract(text, self.state.ticket.to_dict(), task="ticket")
        self.apply_updates(self.state.ticket, extracted)

        errs = self.validator.validate_journey(self.state.ticket)
        if errs:
            return self.prompts.validation_errors(errs)

        missing = self.state.ticket.missing_slots()
        action = decide_next_ticket_action(missing)

        if action == "ticket_complete":
            self.confirm_ticket = True
            return self.prompts.confirm_summary(self.state.ticket.summary())

        return action

    def _delay_flow(self, text: str) -> str:
        extracted = self.parser.extract(text, self.state.delay.to_dict(), task="delay")
        self.apply_updates(self.state.delay, extracted)

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

    def _confirm_ticket(self, text: str) -> str:
        ans = text.lower().strip()
        if ans in {"yes", "y"}:
            result = self.ticket_search.search_cheapest(self.state.ticket.to_dict())
            self.confirm_ticket = False
            self.state.current_task = None
            return (
                "Great - your journey details are complete.\n\n"
                f"{result['message']}\n\n"
                "In the final system, this is where the cheapest ticket and booking link will be shown."
            )
        if ans in {"no", "n"}:
            self.confirm_ticket = False
            return (
                "No problem. What needs changing?\n"
                "e.g. 'Change destination to London Waterloo' or 'My return date is 2026-07-30'."
            )
        return "Please answer yes or no."

    def _confirm_delay(self, text: str) -> str:
        ans = text.lower().strip()
        if ans in {"yes", "y"}:
            result = self.delay_predictor.predict_arrival(self.state.delay.to_dict())
            self.confirm_delay = False
            self.state.current_task = None
            return f"Great - the delay details are complete.\n\n{result['message']}"
        if ans in {"no", "n"}:
            self.confirm_delay = False
            return (
                "No problem. What needs changing?\n"
                "e.g. 'The delay is 15 minutes' or 'The current station is Southampton'."
            )
        return "Please answer yes or no."

    def run(self):
        print(self.prompts.greeting())
        while True:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in {"quit", "exit"}:
                print("Bot: Goodbye.")
                break
            print(f"\nBot: {self.handle_user_input(user_input)}")
