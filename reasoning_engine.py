from experta import KnowledgeEngine, Fact, Rule


class RulesEngine(KnowledgeEngine):
    def __init__(self):
        super().__init__()
        self.response = None
        self.action = None

    @Rule(Fact(intent="ticket"))
    def go_ticket(self):
        self.action = "ticket_flow"

    @Rule(Fact(intent="delay"))
    def go_delay(self):
        self.action = "delay_flow"

    @Rule(Fact(intent="faq"))
    def go_faq(self):
        self.action = "faq_flow"

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
    def need_depart(self):
        self.response = "What date are you travelling? (YYYY-MM-DD)"

    @Rule(Fact(task="ticket"), Fact(missing_slot="return_date"))
    def need_return(self):
        self.response = "And your return date? (YYYY-MM-DD)"

    @Rule(Fact(task="ticket"), Fact(complete=True))
    def ticket_done(self):
        self.response = "ticket_complete"

    @Rule(Fact(task="delay"), Fact(missing_slot="train_id"))
    def need_train(self):
        self.response = "Which train are you on? Please enter the train ID or service name."

    @Rule(Fact(task="delay"), Fact(missing_slot="current_station"))
    def need_cur_station(self):
        self.response = "Which station has the train currently reached?"

    @Rule(Fact(task="delay"), Fact(missing_slot="delay_minutes"))
    def need_delay(self):
        self.response = "How many minutes is the train delayed?"

    @Rule(Fact(task="delay"), Fact(missing_slot="destination"))
    def need_dest_station(self):
        self.response = "What is your destination station?"

    @Rule(Fact(task="delay"), Fact(complete=True))
    def delay_done(self):
        self.response = "delay_complete"

    @Rule(Fact(intent="unknown"))
    def no_idea(self):
        self.response = "Sorry, I did not understand that. Could you rephrase it?"


def decide_intent_with_rules(intent):
    eng = RulesEngine()
    eng.reset()
    eng.declare(Fact(intent=intent))
    eng.run()
    return eng.action or "faq_flow"


def decide_next_ticket_action(missing):
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
