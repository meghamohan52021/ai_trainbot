from datetime import datetime
from typing import List, Optional
from station_data import STATION_ALIASES, VALID_STATIONS


class ValidationEngine:
    @staticmethod
    def normalize_station(name: Optional[str]) -> Optional[str]:
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
    def validate_date(date_str: Optional[str]) -> bool:
        if not date_str:
            return False
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_time_pref(pref: Optional[dict]) -> bool:
        if pref is None:
            return True
        if not isinstance(pref, dict):
            return False
        if "type" not in pref or "time" not in pref:
            return False
        if pref["type"] not in {"before", "after", "at", "morning", "afternoon", "evening"}:
            return False
        return True

    @classmethod
    def validate_journey(cls, state) -> List[str]:
        errors = []

        if state.from_station:
            normalized = cls.normalize_station(state.from_station)
            if not normalized:
                errors.append("Departure station is not recognised.")
            else:
                state.from_station = normalized

        if state.to_station:
            normalized = cls.normalize_station(state.to_station)
            if not normalized:
                errors.append("Destination station is not recognised.")
            else:
                state.to_station = normalized

        if state.from_station and state.to_station:
            if state.from_station == state.to_station:
                errors.append("Departure and destination cannot be the same.")

        if state.journey_type and state.journey_type not in {"single", "return"}:
            errors.append("Journey type must be 'single' or 'return'.")

        if state.depart_date and not cls.validate_date(state.depart_date):
            errors.append("Departure date must be in YYYY-MM-DD format.")

        if state.return_date and not cls.validate_date(state.return_date):
            errors.append("Return date must be in YYYY-MM-DD format.")

        if state.depart_date and state.return_date:
            d1 = datetime.strptime(state.depart_date, "%Y-%m-%d")
            d2 = datetime.strptime(state.return_date, "%Y-%m-%d")
            if d2 < d1:
                errors.append("Return date must be after departure date.")

        if not cls.validate_time_pref(state.depart_time_pref):
            errors.append("Departure time preference is invalid.")

        if not cls.validate_time_pref(state.return_time_pref):
            errors.append("Return time preference is invalid.")

        return errors
    
    @classmethod
    def validate_delay(cls, state) -> List[str]:
        errors = []

        if state.current_station:
            normalized = cls.normalize_station(state.current_station)
            if not normalized:
                errors.append("Current station is not recognised.")
            else:
                state.current_station = normalized

        if state.destination:
            normalized = cls.normalize_station(state.destination)
            if not normalized:
                errors.append("Destination station is not recognised.")
            else:
                state.destination = normalized

        if state.current_station and state.destination:
            if state.current_station == state.destination:
                errors.append("Current station and destination cannot be the same.")

        if state.delay_minutes is not None:
            try:
                state.delay_minutes = int(state.delay_minutes)
                if state.delay_minutes < 0:
                    errors.append("Delay minutes cannot be negative.")
            except ValueError:
                errors.append("Delay minutes must be a number.")

        return errors