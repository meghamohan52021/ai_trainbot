class PromptManager:

    @staticmethod
    def greeting() -> str:
        return (
            "Hi! I'm Choo Choo AI. Tell me about your journey, a train delay, "
            "or ask me a rail question and I'll do my best to help."
        )

    @staticmethod
    def fallback() -> str:
        return (
            "Sorry, I didn't quite catch that. You can ask me to find a train ticket, "
            "predict a delay, or answer a rail question. Just tell me what you need."
        )

    @staticmethod
    def ask_for(slot: str, context: dict | None = None) -> str:
        context = context or {}
        known_from = context.get("from_station")
        known_to = context.get("to_station")
        known_date = context.get("depart_date")

        questions = {
            "from_station": (
                "And where are you travelling from?"
                if known_to
                else "Where are you travelling from?"
            ),
            "to_station": (
                f"Got it, travelling from {known_from}. Where are you heading?"
                if known_from
                else "Where are you travelling to?"
            ),
            "journey_type": (
                f"Is your trip to {known_to} a single or return journey?"
                if known_to
                else "Is this a single or return journey?"
            ),
            "depart_date": (
                f"What date are you travelling to {known_to}? You can say something like tomorrow, next Friday or 15 July."
                if known_to
                else "What date are you travelling? You can say something like tomorrow, next Friday or 15 July."
            ),
            "depart_time_pref": (
                f"What time do you want to depart{' on ' + known_date if known_date else ''}? "
                "You can say morning, after 2pm, before 10am, or no preference."
            ),
            "return_date": (
                f"What date are you returning to {known_from}?"
                if known_from
                else "What date are you coming back?"
            ),
            "return_time_pref": (
                "What time do you want to travel back? "
                "For example you could say afternoon, after 4pm, or no preference."
            ),
            "current_station": "Which station has your train just reached?",
            "delay_minutes": (
                "How many minutes is the train currently delayed? "
                "For example you could say 10 minutes or half an hour."
            ),
            "destination": (
                f"And your destination is {known_to}, is that right?"
                if known_to
                else "What is your destination station?"
            ),
        }
        return questions.get(slot, f"Could you tell me your {slot.replace('_', ' ')}?")

    @staticmethod
    def confirm_summary(summary: str) -> str:
        return (
            f"Here is what I have got:\n\n{summary}\n\n"
            "Does that all look correct? (yes or no)"
        )

    @staticmethod
    def validation_errors(errors: list[str]) -> str:
        if len(errors) == 1:
            return f"Just one thing to fix: {errors[0]}"
        return "A couple of things need fixing: " + ", and ".join(errors)

    @staticmethod
    def correction_prompt() -> str:
        return (
            "No problem. What needs changing? You can say things like "
            "change destination, departure date, return time, or just tell me what is wrong."
        )

    @staticmethod
    def not_understood_slot(slot: str) -> str:
        retry = {
            "from_station": "I didn't catch the departure station. Could you give me the full station name?",
            "to_station": "I didn't catch the destination. Could you give me the full station name?",
            "depart_date": "I didn't get that date. Try something like tomorrow, next Monday or 20 July.",
            "depart_time_pref": "I didn't catch the time. Try morning, after 2pm or no preference.",
            "return_date": "I didn't get the return date. Try something like 22 July or next Sunday.",
            "return_time_pref": "I didn't catch the return time. Try afternoon or after 4pm.",
            "journey_type": "I need to know if this is a single or return. Which is it?",
            "current_station": "Which station has the train just reached? Please give the full name.",
            "delay_minutes": "How many minutes delayed is the train? For example 10 minutes or 1 hour.",
            "destination": "What is your destination station? Please give the full name.",
        }
        return retry.get(slot, f"I didn't catch that. Could you tell me your {slot.replace('_', ' ')} again?")

    @staticmethod
    def goodbye() -> str:
        return "Safe travels! Feel free to come back if you need anything else."

    @staticmethod
    def task_complete_ticket() -> str:
        return "Your journey details are confirmed. Searching for the best available tickets now..."

    @staticmethod
    def task_complete_delay() -> str:
        return "Got all the details. Running the delay prediction now..."