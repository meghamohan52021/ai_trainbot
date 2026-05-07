from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List


@dataclass
class JourneyState:
    from_station: Optional[str] = None
    to_station: Optional[str] = None
    journey_type: Optional[str] = None
    depart_date: Optional[str] = None
    depart_time_pref: Optional[Dict] = None
    return_date: Optional[str] = None
    return_time_pref: Optional[Dict] = None
    duration_options: List[int] = field(default_factory=list)

    def missing_slots(self):
        needed = ["from_station", "to_station", "journey_type", "depart_date"]
        if self.journey_type == "return":
            needed.append("return_date")
        return [s for s in needed if getattr(self, s) in (None, "", [])]

    def is_complete(self):
        return len(self.missing_slots()) == 0

    def to_dict(self):
        return asdict(self)

    def summary(self):
        lines = [
            f"From: {self.from_station or 'Not set'}",
            f"To: {self.to_station or 'Not set'}",
            f"Type: {self.journey_type or 'Not set'}",
            f"Depart: {self.depart_date or 'Not set'}",
            f"Depart time pref: {self.depart_time_pref or 'None'}",
        ]
        if self.journey_type == "return":
            lines.append(f"Return: {self.return_date or 'Not set'}")
            lines.append(f"Return time pref: {self.return_time_pref or 'None'}")
        if self.duration_options:
            lines.append(f"Trip duration options: {self.duration_options}")
        return "\n".join(lines)


@dataclass
class DelayState:
    train_id: Optional[str] = None
    current_station: Optional[str] = None
    delay_minutes: Optional[int] = None
    destination: Optional[str] = None

    def missing_slots(self):
        needed = ["train_id", "current_station", "delay_minutes", "destination"]
        return [s for s in needed if getattr(self, s) in (None, "", [])]

    def is_complete(self):
        return len(self.missing_slots()) == 0

    def to_dict(self):
        return asdict(self)

    def summary(self):
        return (
            f"Train/service: {self.train_id or 'Not set'}\n"
            f"Current station: {self.current_station or 'Not set'}\n"
            f"Delay: {self.delay_minutes if self.delay_minutes is not None else 'Not set'} minutes\n"
            f"Destination: {self.destination or 'Not set'}"
        )


@dataclass
class ChatState:
    current_task: Optional[str] = None
    ticket: JourneyState = field(default_factory=JourneyState)
    delay: DelayState = field(default_factory=DelayState)

    def reset(self):
        self.current_task = None
        self.ticket = JourneyState()
        self.delay = DelayState()
