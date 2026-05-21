import json
import os
import requests


class LLMClient:
    # This class is a fallback NLU parser that uses an external LLM API 
    #to extract structured data from user input

    def __init__(self):
        self.enabled = os.getenv("USE_LLM_FALLBACK", "false").lower() == "true"
        self.api_url = os.getenv("LLM_API_URL", "")
        self.api_key = os.getenv("LLM_API_KEY", "")

    def extract_structured_data(self, text: str, current_state: dict) -> dict:
        if not self.enabled or not self.api_url:
            return {}

        prompt = f"""
You are a fallback NLU parser for a UK train chatbot.
Extract structured data only. Do not answer the user.

Allowed intents: ticket, delay, faq, unknown.

Return valid JSON with these fields:
intent, from_station, to_station, journey_type, depart_date, depart_time_pref,
return_date, return_time_pref, train_id, current_station, delay_minutes, destination,
confidence.

User text: {text}
Current state: {current_state}
"""

        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={"prompt": prompt},
                timeout=8
            )
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and "text" in data:
                return json.loads(data["text"])

            return data if isinstance(data, dict) else {}

        except Exception:
            return {}