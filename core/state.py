from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List
from datetime import date


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
        needed = [
            "from_station",
            "to_station",
            "journey_type",
            "depart_date",
            "depart_time_pref",
        ]
        if self.journey_type == "return":
            # "open" is a valid return_date value — user has chosen an open return
            if self.return_date != "open":
                needed.append("return_date")
        return [slot for slot in needed if getattr(self, slot) in (None, "", [])]

    def is_complete(self):
        return len(self.missing_slots()) == 0

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def _format_date(d: Optional[str]) -> str:
        if not d:
            return "Not set"
        if d == "open":
            return "Open return (flexible)"
        try:
            return date.fromisoformat(d).strftime("%A %d %B %Y")
        except Exception:
            return d

    @staticmethod
    def _format_time_pref(pref) -> str:
        if not pref:
            return "No preference"
        t = pref.get("type")
        if t == "any":
            return "No preference"
        if t == "between":
            labels = {
                ("07:00", "11:59"): "Morning",
                ("12:00", "17:59"): "Afternoon",
                ("18:00", "21:59"): "Evening",
                ("20:00", "23:59"): "Night",
            }
            key = (pref.get("start"), pref.get("end"))
            return labels.get(key, f"{pref.get('start')} to {pref.get('end')}")
        if t == "before":
            return f"Before {pref.get('time')}"
        if t == "after":
            return f"After {pref.get('time')}"
        if t == "at":
            return f"At {pref.get('time')}"
        return str(pref)

    def summary(self):
        journey_label = (
            "Single" if self.journey_type == "single"
            else "Return" if self.journey_type == "return"
            else "Not set"
        )
        lines = [
            f"From: {self.from_station or 'Not set'}",
            f"To: {self.to_station or 'Not set'}",
            f"Journey type: {journey_label}",
            f"Departure: {self._format_date(self.depart_date)}, {self._format_time_pref(self.depart_time_pref)}",
        ]
        if self.journey_type == "return":
            if self.return_date == "open":
                lines.append("Return: Open return (flexible date)")
            else:
                lines.append(f"Return: {self._format_date(self.return_date)}, {self._format_time_pref(self.return_time_pref)}")
        return "\n".join(lines)


@dataclass
class DelayState:
    train_id: Optional[str] = None
    current_station: Optional[str] = None
    delay_minutes: Optional[int] = None
    destination: Optional[str] = None

    def missing_slots(self):
        needed = ["current_station", "delay_minutes", "destination"]
        return [slot for slot in needed if getattr(self, slot) in (None, "", [])]

    def is_complete(self):
        return len(self.missing_slots()) == 0

    def to_dict(self):
        return asdict(self)

    def summary(self):
        delay_text = (
            f"{self.delay_minutes} minutes"
            if self.delay_minutes is not None
            else "Not set"
        )
        return (
            f"Current station: {self.current_station or 'Not set'}\n"
            f"Current delay: {delay_text}\n"
            f"Destination: {self.destination or 'Not set'}"
        )


@dataclass
class ChatState:
    current_task: Optional[str] = None
    ticket: JourneyState = field(default_factory=JourneyState)
    delay: DelayState = field(default_factory=DelayState)
    last_intent: Optional[str] = None
    last_confidence: float = 0.0
    last_nlu_source: Optional[str] = None
    pending_correction_slot: Optional[str] = None

    def reset(self):
        self.current_task = None
        self.ticket = JourneyState()
        self.delay = DelayState()
        self.last_intent = None
        self.last_confidence = 0.0
        self.last_nlu_source = None
        self.pending_correction_slot = None