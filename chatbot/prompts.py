class PromptManager:
    @staticmethod
    def greeting() -> str:
        return (
            "Hello, I can help you find the cheapest train ticket in the UK.\n"
            "Tell me about your journey in your own words."
        )

    @staticmethod
    def fallback() -> str:
        return "Sorry, I did not understand that. Could you rephrase it?"

    @staticmethod
    def ask_for(slot: str) -> str:
        questions = {
            "from_station": "Where are you travelling from?",
            "to_station": "Where are you travelling to?",
            "journey_type": "Is this a single or return journey?",
            "depart_date": "What is your departure date? Please use YYYY-MM-DD.",
            "return_date": "What is your return date? Please use YYYY-MM-DD.",
        }
        return questions.get(slot, f"Please provide: {slot}")

    @staticmethod
    def confirm_summary(summary: str) -> str:
        return f"Thanks. Here is your journey summary:\n\n{summary}\n\nIs this correct? (yes/no)"

    @staticmethod
    def validation_errors(errors: list[str]) -> str:
        return "I found some issues:\n- " + "\n- ".join(errors)