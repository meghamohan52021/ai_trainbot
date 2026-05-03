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

        self.awaiting_ticket_confirmation = False
        self.awaiting_delay_confirmation = False

    def apply_extraction(self, target_state, data: dict) -> None:
        for key, value in data.items():
            if not hasattr(target_state, key):
                continue

            current_value = getattr(target_state, key)

            if value not in (None, "", []):
                if current_value in (None, "", []):
                    setattr(target_state, key, value)

    def handle_user_input(self, text: str) -> str:
        if text.lower().strip() in {"restart", "reset"}:
            self.state.reset()
            self.awaiting_ticket_confirmation = False
            self.awaiting_delay_confirmation = False
            return "Conversation reset. How can I help you?"

        if self.awaiting_ticket_confirmation:
            return self.handle_ticket_confirmation(text)

        if self.awaiting_delay_confirmation:
            return self.handle_delay_confirmation(text)

        if self.state.current_task is None:
            detected_intent = self.parser.detect_intent(text)
            flow = decide_intent_with_rules(detected_intent)

            if flow == "ticket_flow":
                self.state.current_task = "ticket"
            elif flow == "delay_flow":
                self.state.current_task = "delay"
            else:
                kb_answer = self.kb.search(text)
                if kb_answer:
                    return kb_answer
                return self.prompts.fallback()

        if self.state.current_task == "ticket":
            return self.handle_ticket_flow(text)

        if self.state.current_task == "delay":
            return self.handle_delay_flow(text)

        kb_answer = self.kb.search(text)
        if kb_answer:
            return kb_answer

        return self.prompts.fallback()

    def handle_ticket_flow(self, text: str) -> str:
        extracted = self.parser.extract(
            text,
            self.state.ticket.to_dict(),
            task="ticket"
        )

        self.apply_extraction(self.state.ticket, extracted)

        errors = self.validator.validate_journey(self.state.ticket)
        if errors:
            return self.prompts.validation_errors(errors)

        missing = self.state.ticket.missing_slots()
        action = decide_next_ticket_action(missing)

        if action == "ticket_complete":
            self.awaiting_ticket_confirmation = True
            return self.prompts.confirm_summary(self.state.ticket.summary())

        return action

    def handle_delay_flow(self, text: str) -> str:
        extracted = self.parser.extract(
            text,
            self.state.delay.to_dict(),
            task="delay"
        )

        self.apply_extraction(self.state.delay, extracted)

        errors = self.validator.validate_delay(self.state.delay)
        if errors:
            return self.prompts.validation_errors(errors)

        missing = self.state.delay.missing_slots()
        action = decide_next_delay_action(missing)

        if action == "delay_complete":
            self.awaiting_delay_confirmation = True
            return (
                "Thanks. Here is the delay information I collected:\n\n"
                f"{self.state.delay.summary()}\n\n"
                "Is this correct? (yes/no)"
            )

        return action

    def handle_ticket_confirmation(self, text: str) -> str:
        answer = text.lower().strip()

        if answer in {"yes", "y"}:
            result = self.ticket_search.search_cheapest(self.state.ticket.to_dict())

            self.awaiting_ticket_confirmation = False
            self.state.current_task = None

            return (
                "Great — your journey details are complete.\n\n"
                f"{result['message']}\n\n"
                "In the final system, this is where the cheapest ticket and booking link will be shown."
            )

        if answer in {"no", "n"}:
            self.awaiting_ticket_confirmation = False
            return (
                "No problem. Please tell me what needs changing.\n"
                "For example: 'Change destination to London Waterloo' or "
                "'My return date is 2026-07-30'."
            )

        return "Please answer yes or no."

    def handle_delay_confirmation(self, text: str) -> str:
        answer = text.lower().strip()

        if answer in {"yes", "y"}:
            result = self.delay_predictor.predict_arrival(self.state.delay.to_dict())

            self.awaiting_delay_confirmation = False
            self.state.current_task = None

            return (
                "Great — the delay details are complete.\n\n"
                f"{result['message']}"
            )

        if answer in {"no", "n"}:
            self.awaiting_delay_confirmation = False
            return (
                "No problem. Please tell me what needs changing.\n"
                "For example: 'The delay is 15 minutes' or "
                "'The current station is Southampton'."
            )

        return "Please answer yes or no."

    def run(self) -> None:
        print(self.prompts.greeting())

        while True:
            user_input = input("\nYou: ").strip()

            if user_input.lower() in {"quit", "exit"}:
                print("Bot: Goodbye.")
                break

            response = self.handle_user_input(user_input)
            print(f"\nBot: {response}")