from datetime import datetime
from typing import List, Optional
from station_data import STATION_ALIASES


class ValidationEngine:
    @staticmethod
    def normalise(name: Optional[str]) -> Optional[str]:
        if not name:
            return None
        cleaned = name.strip().lower()
        if cleaned in STATION_ALIASES:
            return STATION_ALIASES[cleaned]
        for _, official in STATION_ALIASES.items():
            if cleaned == official.lower():
                return official
        return None

    @staticmethod
    def valid_date(value: Optional[str]) -> bool:
        if not value:
            return False
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    @staticmethod
    def valid_time_pref(pref: Optional[dict]) -> bool:
        if pref is None:
            return True
        if not isinstance(pref, dict):
            return False

        pref_type = pref.get("type")
        if pref_type in {"before", "after", "at"}:
            return isinstance(pref.get("time"), str) and bool(pref.get("time"))
        if pref_type == "between":
            return isinstance(pref.get("start"), str) and isinstance(pref.get("end"), str)
        if pref_type == "any":
            return True

        #Backwards compatibility with old parser outputs
        if pref_type in {"morning", "afternoon", "evening"}:
            return True

        return False

    @classmethod
    def validate_journey(cls, state) -> List[str]:
        errors = []

        if state.from_station:
            normalised = cls.normalise(state.from_station)
            if not normalised:
                errors.append("Departure station not recognised.")
            else:
                state.from_station = normalised

        if state.to_station:
            normalised = cls.normalise(state.to_station)
            if not normalised:
                errors.append("Destination station not recognised.")
            else:
                state.to_station = normalised

        if state.from_station and state.to_station and state.from_station == state.to_station:
            errors.append("Departure and destination cannot be the same.")

        if state.journey_type and state.journey_type not in {"single", "return"}:
            errors.append("Journey type must be single or return.")

        if state.depart_date and not cls.valid_date(state.depart_date):
            errors.append("Departure date must be YYYY-MM-DD.")

        if state.return_date and not cls.valid_date(state.return_date):
            errors.append("Return date must be YYYY-MM-DD.")

        if state.depart_date and state.return_date:
            depart = datetime.strptime(state.depart_date, "%Y-%m-%d")
            ret = datetime.strptime(state.return_date, "%Y-%m-%d")
            if ret < depart:
                errors.append("Return date must be after the departure date.")

        if not cls.valid_time_pref(state.depart_time_pref):
            errors.append("Departure time preference is invalid.")

        if not cls.valid_time_pref(state.return_time_pref):
            errors.append("Return time preference is invalid.")

        return errors

    @classmethod
    def validate_delay(cls, state) -> List[str]:
        errors = []

        if state.current_station:
            normalised = cls.normalise(state.current_station)
            if not normalised:
                errors.append("Current station not recognised.")
            else:
                state.current_station = normalised

        if state.destination:
            normalised = cls.normalise(state.destination)
            if not normalised:
                errors.append("Destination station not recognised.")
            else:
                state.destination = normalised

        if state.current_station and state.destination and state.current_station == state.destination:
            errors.append("Current station and destination cannot be the same.")

        if state.delay_minutes is not None:
            try:
                state.delay_minutes = int(state.delay_minutes)
                if state.delay_minutes < 0:
                    errors.append("Delay cannot be negative.")
            except (TypeError, ValueError):
                errors.append("Delay must be a number of minutes.")

        return errors
