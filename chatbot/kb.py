class KnowledgeBase:
    """
    stores domain knowledge as question/answer style rules.
    """

    def __init__(self):
        self.faqs = {
            "off peak": (
                "Off-peak tickets are usually cheaper tickets for travelling at less busy times. "
                "The exact valid times depend on the route and train company."
            ),
            "peak": (
                "Peak tickets are usually used during busy travel times, often morning and evening commuter times."
            ),
            "single": (
                "A single ticket is for one-way travel only."
            ),
            "return": (
                "A return ticket lets you travel to your destination and come back again."
            ),
            "railcard": (
                "A railcard can give passengers discounted train fares if they are eligible."
            ),
            "delay repay": (
                "Delay Repay is a compensation scheme used by many UK train companies when a journey is delayed. "
                "The exact compensation depends on the operator and delay length."
            ),
            "cheapest": (
                "To find the cheapest ticket, I need your departure station, destination, travel date, "
                "time preference, and whether it is a single or return journey."
            ),
            "api": (
                "The ticket search component can later connect to a National Rail or booking API. "
                "For now, this chatbot prepares a clean journey dictionary for that component."
            ),
            "station": (
                "Station names and aliases are stored separately so the chatbot can normalise names like "
                "'London' into a more specific station name."
            )
        }

    def search(self, user_text):
        """
        Search the KB using simple keyword matching.
        This is deliberately simple and explainable for coursework.
        """
        text = user_text.lower()

        for keyword, answer in self.faqs.items():
            if keyword in text:
                return answer

        return None