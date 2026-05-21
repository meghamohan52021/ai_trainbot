import collections
import collections.abc

if not hasattr(collections, "Mapping"):
    collections.Mapping = collections.abc.Mapping

if not hasattr(collections, "MutableMapping"):
    collections.MutableMapping = collections.abc.MutableMapping

if not hasattr(collections, "Sequence"):
    collections.Sequence = collections.abc.Sequence

from experta import KnowledgeEngine, Fact, Rule


class RulesEngine(KnowledgeEngine):
    """
    Uses extracted facts to route the train chatbot intent, ask 
    the next missing ticket or delay question, and complete the 
    task when all required details are filled
    """

    def __init__(self):
        super().__init__()
        self.response = None
        self.action = None

    
    #Intent routing rules
    @Rule(Fact(intent="ticket"))
    def go_ticket(self):
        self.action = "ticket_flow"

    @Rule(Fact(intent="delay"))
    def go_delay(self):
        self.action = "delay_flow"

    @Rule(Fact(intent="faq"))
    def go_faq(self):
        self.action = "faq_flow"

    @Rule(Fact(intent="unknown"))
    def no_idea(self):
        self.response = "Sorry, I did not understand that. Could you rephrase it?"

    
    #Ticket missing-slot rules
    @Rule(Fact(task="ticket"), Fact(missing_slot="from_station"))
    def need_origin(self):
        self.response = "Where are you travelling from?"

    @Rule(Fact(task="ticket"), Fact(missing_slot="to_station"))
    def need_dest(self):
        self.response = "Where are you travelling to?"

    @Rule(Fact(task="ticket"), Fact(missing_slot="journey_type"))
    def need_type(self):
        self.response = "Is this a single or return journey?"

    @Rule(Fact(task="ticket"), Fact(missing_slot="depart_date"))
    def need_depart_date(self):
        self.response = (
            "What date are you travelling? "
            "You can say 'tomorrow', 'day after tomorrow', 'next Tuesday', or '15 July'."
        )

    @Rule(Fact(task="ticket"), Fact(missing_slot="depart_time_pref"))
    def need_depart_time(self):
        self.response = (
            "What time would you prefer to depart? "
            "You can say 'morning', 'afternoon', 'before 10am', 'after 2pm', "
            "or 'no preference'."
        )

    @Rule(Fact(task="ticket"), Fact(missing_slot="return_date"))
    def need_return_date(self):
        self.response = (
            "What date are you coming back? "
            "You can say 'tomorrow', 'day after tomorrow', 'next Tuesday', or '15 July'."
        )

    @Rule(Fact(task="ticket"), Fact(missing_slot="return_time_pref"))
    def need_return_time(self):
        self.response = (
            "What return time would you prefer? "
            "You can say 'afternoon', 'after 2pm', 'evening', or 'no preference'."
        )

    @Rule(Fact(task="ticket"), Fact(complete=True))
    def ticket_done(self):
        self.response = "ticket_complete"

    # Delay missing-slot rules
    @Rule(Fact(task="delay"), Fact(missing_slot="train_id"))
    def need_train(self):
        self.response = "Which train are you on? Please enter the train ID or service name."

    @Rule(Fact(task="delay"), Fact(missing_slot="current_station"))
    def need_cur_station(self):
        self.response = "Which station has the train currently reached?"

    @Rule(Fact(task="delay"), Fact(missing_slot="delay_minutes"))
    def need_delay(self):
        self.response = "How many minutes is the train delayed? You can say '15 minutes' or 'fifteen minutes'."

    @Rule(Fact(task="delay"), Fact(missing_slot="destination"))
    def need_dest_station(self):
        self.response = "What is your destination station?"

    @Rule(Fact(task="delay"), Fact(complete=True))
    def delay_done(self):
        self.response = "delay_complete"


def decide_intent_with_rules(intent):
    #Route to the correct flow based on detected intent, or return a fallback response if intent is unknown
    eng = RulesEngine()
    eng.reset()
    eng.declare(Fact(intent=intent))
    eng.run()
    return eng.action or "faq_flow"


def decide_next_ticket_action(missing):
    #decide next ticket question based on the first missing slot
    eng = RulesEngine()
    eng.reset()

    if not missing:
        eng.declare(Fact(task="ticket"))
        eng.declare(Fact(complete=True))
    else:
        eng.declare(Fact(task="ticket"))
        eng.declare(Fact(missing_slot=missing[0]))

    eng.run()
    return eng.response


def decide_next_delay_action(missing):
    #Decide next delay question based on the first missing slot
    eng = RulesEngine()
    eng.reset()

    if not missing:
        eng.declare(Fact(task="delay"))
        eng.declare(Fact(complete=True))
    else:
        eng.declare(Fact(task="delay"))
        eng.declare(Fact(missing_slot=missing[0]))

    eng.run()
    return eng.response


def post_prediction_advice(predicted_delay: int):
    #Provide advice based on the predicted delay duration for delay claims eligibility
    if predicted_delay >= 120:
        return "You may be eligible for a strong Delay Repay claim because the predicted delay is over 120 minutes."
    if predicted_delay >= 60:
        return "You may be eligible for Delay Repay because the predicted delay is over 60 minutes."
    if predicted_delay >= 30:
        return "You may be eligible for Delay Repay because the predicted delay is over 30 minutes."
    if predicted_delay >= 15:
        return "You may be eligible for Delay Repay because the predicted delay is over 15 minutes."
    return "The predicted delay is under 15 minutes, so compensation is less likely."
