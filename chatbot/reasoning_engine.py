from experta import KnowledgeEngine, Fact, Rule


class ChatbotReasoningEngine(KnowledgeEngine):
    """
    Rule-based reasoning engine for the chatbot.

    1. Facts describe the current chatbot situation.
    2. Rules decide what the chatbot should do next.
    """

    def __init__(self):
        super().__init__()
        self.response = None
        self.action = None

    #Task routing rules

    @Rule(Fact(intent="ticket"))
    def route_ticket(self):
        self.action = "ticket_flow"

    @Rule(Fact(intent="delay"))
    def route_delay(self):
        self.action = "delay_flow"

    @Rule(Fact(intent="faq"))
    def route_faq(self):
        self.action = "faq_flow"

    #Ticket missing-slot rules

    @Rule(Fact(task="ticket"), Fact(missing_slot="from_station"))
    def ask_from_station(self):
        self.response = "Where are you travelling from?"

    @Rule(Fact(task="ticket"), Fact(missing_slot="to_station"))
    def ask_to_station(self):
        self.response = "Where are you travelling to?"

    @Rule(Fact(task="ticket"), Fact(missing_slot="journey_type"))
    def ask_journey_type(self):
        self.response = "Is this a single or return journey?"

    @Rule(Fact(task="ticket"), Fact(missing_slot="depart_date"))
    def ask_depart_date(self):
        self.response = "What is your departure date? Please use YYYY-MM-DD."

    @Rule(Fact(task="ticket"), Fact(missing_slot="return_date"))
    def ask_return_date(self):
        self.response = "What is your return date? Please use YYYY-MM-DD."

    @Rule(Fact(task="ticket"), Fact(complete=True))
    def ticket_complete(self):
        self.response = "ticket_complete"

    #Delay missing-slot rules

    @Rule(Fact(task="delay"), Fact(missing_slot="train_id"))
    def ask_train_id(self):
        self.response = "Which train are you on? Please enter the train ID or service name."

    @Rule(Fact(task="delay"), Fact(missing_slot="current_station"))
    def ask_current_station(self):
        self.response = "Which station has the train currently reached?"

    @Rule(Fact(task="delay"), Fact(missing_slot="delay_minutes"))
    def ask_delay_minutes(self):
        self.response = "How many minutes is the train delayed?"

    @Rule(Fact(task="delay"), Fact(missing_slot="destination"))
    def ask_destination(self):
        self.response = "What is your destination station?"

    @Rule(Fact(task="delay"), Fact(complete=True))
    def delay_complete(self):
        self.response = "delay_complete"

    #Fallback rule

    @Rule(Fact(intent="unknown"))
    def fallback(self):
        self.response = "Sorry, I did not understand that. Could you rephrase it?"


def decide_intent_with_rules(intent):
    """
    Uses Experta to decide the high-level flow.
    """
    engine = ChatbotReasoningEngine()
    engine.reset()
    engine.declare(Fact(intent=intent))
    engine.run()

    return engine.action or "faq_flow"


def decide_next_ticket_action(missing_slots):
    """
    Uses Experta to decide the next question for Task 1.
    """
    engine = ChatbotReasoningEngine()
    engine.reset()

    if len(missing_slots) == 0:
        engine.declare(Fact(task="ticket"))
        engine.declare(Fact(complete=True))
    else:
        engine.declare(Fact(task="ticket"))
        engine.declare(Fact(missing_slot=missing_slots[0]))

    engine.run()
    return engine.response


def decide_next_delay_action(missing_slots):
    """
    Uses Experta to decide the next question for Task 2.
    """
    engine = ChatbotReasoningEngine()
    engine.reset()

    if len(missing_slots) == 0:
        engine.declare(Fact(task="delay"))
        engine.declare(Fact(complete=True))
    else:
        engine.declare(Fact(task="delay"))
        engine.declare(Fact(missing_slot=missing_slots[0]))

    engine.run()
    return engine.response