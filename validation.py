from datetime import datetime
from typing import List, Optional
from station_data import STATION_ALIASES, VALID_STATIONS
from config import now_london


class ValidationEngine:
    @staticmethod
    def normalise(name: Optional[str]) -> Optional[str]:
        if not name:
            return None
        cleaned = name.strip().lower()
        if cleaned in STATION_ALIASES:
            return STATION_ALIASES[cleaned]
        for alias, official in STATION_ALIASES.items():
            if cleaned == official.lower():
                return official
        return None

    @staticmethod
    def valid_date(s: Optional[str]) -> bool:
        if not s:
            return False
        try:
            datetime.strptime(s, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    @staticmethod
    def valid_time_pref(pref: Optional[dict]) -> bool:
        if pref is None:
            return True
        if not isinstance(pref, dict):
            return False
        if "type" not in pref or "time" not in pref:
            return False
        return pref["type"] in {"before", "after", "at", "morning", "afternoon", "evening"}

    @classmethod
    def validate_journey(cls, state) -> List[str]:
        errors = []

        if state.from_station:
            n = cls.normalise(state.from_station)
            if not n:
                errors.append("Departure station not recognised.")
            else:
                state.from_station = n

        if state.to_station:
            n = cls.normalise(state.to_station)
            if not n:
                errors.append("Destination station not recognised.")
            else:
                state.to_station = n

        if state.from_station and state.to_station and state.from_station == state.to_station:
            errors.append("Departure and destination cannot be the same.")

        if state.journey_type and state.journey_type not in {"single", "return"}:
            errors.append("Journey type must be single or return.")

        if state.depart_date and not cls.valid_date(state.depart_date):
            errors.append("Departure date must be YYYY-MM-DD.")

        if state.return_date and not cls.valid_date(state.return_date):
            errors.append("Return date must be YYYY-MM-DD.")

        if state.depart_date and state.return_date:
            d1 = datetime.strptime(state.depart_date, "%Y-%m-%d")
            d2 = datetime.strptime(state.return_date, "%Y-%m-%d")
            if d2 < d1:
                errors.append("Return date must be after departure date.")

        if not cls.valid_time_pref(state.depart_time_pref):
            errors.append("Departure time preference is invalid.")

        if not cls.valid_time_pref(state.return_time_pref):
            errors.append("Return time preference is invalid.")

        return errors

    @classmethod
    def validate_delay(cls, state) -> List[str]:
        errors = []

        if state.current_station:
            n = cls.normalise(state.current_station)
            if not n:
                errors.append("Current station not recognised.")
            else:
                state.current_station = n

        if state.destination:
            n = cls.normalise(state.destination)
            if not n:
                errors.append("Destination not recognised.")
            else:
                state.destination = n

        if state.current_station and state.destination and state.current_station == state.destination:
            errors.append("Current station and destination cannot be the same.")

        if state.delay_minutes is not None:
            try:
                state.delay_minutes = int(state.delay_minutes)
                if state.delay_minutes < 0:
                    errors.append("Delay cannot be negative.")
            except ValueError:
                errors.append("Delay must be a number.")

        return errors
