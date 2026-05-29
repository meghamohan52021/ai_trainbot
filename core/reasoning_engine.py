import collections
import collections.abc

if not hasattr(collections, "Mapping"):
    collections.Mapping = collections.abc.Mapping
if not hasattr(collections, "MutableMapping"):
    collections.MutableMapping = collections.abc.MutableMapping
if not hasattr(collections, "Sequence"):
    
    collections.Sequence = collections.abc.Sequence
#Experta-based reasoning engine for TrainBot
from typing import Any, List, Optional

from experta import Fact, KnowledgeEngine, MATCH, P, Rule


class ReasoningFact(Fact):
    #Fact object used by the Experta rule engine
    pass


TICKET_QUESTIONS = {
    "from_station": "Where are you travelling from?",
    "to_station": "Where are you travelling to?",
    "journey_type": "Is this a single or return journey?",
    "depart_date": "What date are you travelling? You can say 'tomorrow', 'next Tuesday', or '15 July'.",
    "depart_time_pref": "What time would you prefer to depart? You can say 'morning', 'before 10am', 'after 2pm', or 'no preference'.",
    "return_date": "What date are you coming back?",
    "return_time_pref": "What return time would you prefer? For example, 'after 2pm' or 'no preference'.",
}

DELAY_QUESTIONS = {
    "current_station": "Which station has the train currently reached?",
    "delay_minutes": "How many minutes is the train delayed? For example, '10 minutes'.",
    "destination": "What is your destination station?",
}


class TrainBotReasoningEngine(KnowledgeEngine):

    def __init__(self):
        super().__init__()
        self.decision: Optional[str] = None

    @Rule(ReasoningFact(kind="intent", intent="ticket"))
    def route_ticket_intent(self):
        self.decision = "ticket_flow"

    @Rule(ReasoningFact(kind="intent", intent="delay"))
    def route_delay_intent(self):
        self.decision = "delay_flow"

    @Rule(ReasoningFact(kind="intent", intent=MATCH.intent))
    def route_other_intent(self, intent):
        if self.decision is None:
            self.decision = "faq_flow"

    @Rule(ReasoningFact(kind="ticket", complete=True))
    def ticket_is_complete(self):
        self.decision = "ticket_complete"

    @Rule(ReasoningFact(kind="ticket", complete=False, first_missing=MATCH.slot))
    def ask_for_missing_ticket_slot(self, slot):
        self.decision = TICKET_QUESTIONS.get(slot, f"Please provide: {slot}")

    @Rule(ReasoningFact(kind="delay", complete=True))
    def delay_is_complete(self):
        self.decision = "delay_complete"

    @Rule(ReasoningFact(kind="delay", complete=False, first_missing=MATCH.slot))
    def ask_for_missing_delay_slot(self, slot):
        self.decision = DELAY_QUESTIONS.get(slot, f"Please provide: {slot}")

    @Rule(
        ReasoningFact(kind="prediction_advice", predicted_delay=P(lambda d: float(d) >= 120)),
        salience=40,
    )
    def advise_delay_120(self):
        self.decision = (
            "You may be eligible for a strong Delay Repay claim because the predicted delay is over 120 minutes."
        )

    @Rule(
        ReasoningFact(kind="prediction_advice", predicted_delay=P(lambda d: 60 <= float(d) < 120)),
        salience=30,
    )
    def advise_delay_60(self):
        self.decision = "You may be eligible for Delay Repay because the predicted delay is over 60 minutes."

    @Rule(
        ReasoningFact(kind="prediction_advice", predicted_delay=P(lambda d: 30 <= float(d) < 60)),
        salience=20,
    )
    def advise_delay_30(self):
        self.decision = "You may be eligible for Delay Repay because the predicted delay is over 30 minutes."

    @Rule(
        ReasoningFact(kind="prediction_advice", predicted_delay=P(lambda d: 15 <= float(d) < 30)),
        salience=10,
    )
    def advise_delay_15(self):
        self.decision = "You may be eligible for Delay Repay because the predicted delay is over 15 minutes."

    @Rule(
        ReasoningFact(kind="prediction_advice", predicted_delay=P(lambda d: float(d) < 15)),
        salience=0,
    )
    def advise_delay_under_15(self):
        self.decision = "The predicted delay is under 15 minutes, so compensation is less likely."


def _run_engine(fact_data: dict[str, Any], default: str) -> str:
    engine = TrainBotReasoningEngine()
    engine.reset()
    engine.declare(ReasoningFact(**fact_data))
    engine.run()
    return engine.decision or default


def _first_missing(missing: List[str]) -> Optional[str]:
    return missing[0] if missing else None


def decide_intent_with_rules(intent: str) -> str:
    #Decide which main flow the chatbot should use.
    return _run_engine(
        {"kind": "intent", "intent": intent},
        default="faq_flow",
    )


def decide_next_ticket_action(missing: List[str]) -> str:
    #Decide the next ticket-flow action from the missing ticket slots.
    complete = not missing
    return _run_engine(
        {
            "kind": "ticket",
            "complete": complete,
            "first_missing": _first_missing(missing),
        },
        default="ticket_complete" if complete else f"Please provide: {_first_missing(missing)}",
    )


def decide_next_delay_action(missing: List[str]) -> str:
    #Decide the next delay-flow action from the missing delay slots.
    complete = not missing
    return _run_engine(
        {
            "kind": "delay",
            "complete": complete,
            "first_missing": _first_missing(missing),
        },
        default="delay_complete" if complete else f"Please provide: {_first_missing(missing)}",
    )


def post_prediction_advice(predicted_delay) -> str:
    #Give Delay Repay style advice after the prediction model returns a delay.
    return _run_engine(
        {"kind": "prediction_advice", "predicted_delay": float(predicted_delay)},
        default="The predicted delay could not be assessed for Delay Repay advice.",
    )
