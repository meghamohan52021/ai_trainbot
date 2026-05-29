import re


class SlotManager:
    def detect_corrections(self, text: str, task: str):
        lower = text.lower()
        clear = []

        if task == "ticket":
            if any(x in lower for x in ["change destination", "destination to", "travelling to", "going to"]):
                clear.append("to_station")

            if any(x in lower for x in ["change departure", "from station", "travelling from", "departing from"]):
                clear.append("from_station")

            if any(x in lower for x in ["change date", "departure date", "depart date"]):
                clear.append("depart_date")

            if any(x in lower for x in ["return date", "coming back", "come back"]):
                clear.append("return_date")

            if "single" in lower or "return" in lower:
                clear.append("journey_type")

        if task == "delay":
            if "current station" in lower or "currently at" in lower or "now at" in lower:
                clear.append("current_station")

            if "destination" in lower or "going to" in lower:
                clear.append("destination")

            if "delay" in lower or "late" in lower or "minutes" in lower or "mins" in lower:
                clear.append("delay_minutes")

            if "train" in lower or "service" in lower:
                clear.append("train_id")

        return list(dict.fromkeys(clear))

    def clear_slots(self, state_obj, slots):
        for slot in slots:
            if hasattr(state_obj, slot):
                setattr(state_obj, slot, None)

    def apply_updates(self, target, data: dict):
        for key, val in data.items():
            if hasattr(target, key) and val not in (None, "", []):
                setattr(target, key, val)