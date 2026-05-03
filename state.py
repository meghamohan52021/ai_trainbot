from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List


@dataclass
class JourneyState:
    from_station: Optional[str] = None
    to_station: Optional[str] = None
    journey_type: Optional[str] = None  # single / return
    depart_date: Optional[str] = None   # YYYY-MM-DD
    depart_time_pref: Optional[Dict] = None
    return_date: Optional[str] = None
    return_time_pref: Optional[Dict] = None
    duration_options: List[int] = field(default_factory=list)

    def missing_slots(self) -> List[str]:
        required = ["from_station", "to_station", "journey_type", "depart_date"]

        if self.journey_type == "return":
            required.append("return_date")

        return [slot for slot in required if getattr(self, slot) in (None, "", [])]

    def is_complete(self) -> bool:
        return len(self.missing_slots()) == 0

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        parts = [
            f"From: {self.from_station or 'Not set'}",
            f"To: {self.to_station or 'Not set'}",
            f"Journey type: {self.journey_type or 'Not set'}",
            f"Departure date: {self.depart_date or 'Not set'}",
            f"Departure time preference: {self.depart_time_pref or 'Not set'}",
            f"Return date: {self.return_date or 'Not set'}",
            f"Return time preference: {self.return_time_pref or 'Not set'}",
        ]

        if self.duration_options:
            parts.append(f"Possible trip durations: {self.duration_options}")

        return "\n".join(parts)


@dataclass
class DelayState:
    train_id: Optional[str] = None
    current_station: Optional[str] = None
    delay_minutes: Optional[int] = None
    destination: Optional[str] = None

    def missing_slots(self) -> List[str]:
        required = ["train_id", "current_station", "delay_minutes", "destination"]
        return [slot for slot in required if getattr(self, slot) in (None, "", [])]

    def is_complete(self) -> bool:
        return len(self.missing_slots()) == 0

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        parts = [
            f"Train/service: {self.train_id or 'Not set'}",
            f"Current station: {self.current_station or 'Not set'}",
            f"Current delay: {self.delay_minutes if self.delay_minutes is not None else 'Not set'} minutes",
            f"Destination: {self.destination or 'Not set'}",
        ]
        return "\n".join(parts)


@dataclass
class ChatState:
    current_task: Optional[str] = None  # ticket / delay / faq
    ticket: JourneyState = field(default_factory=JourneyState)
    delay: DelayState = field(default_factory=DelayState)

    def reset(self):
        self.current_task = None
        self.ticket = JourneyState()
        self.delay = DelayState()