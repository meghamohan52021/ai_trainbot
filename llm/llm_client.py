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
You are an optional fallback NLU parser for a UK train chatbot.

Your task is to extract structured information from the user's message.
Do not answer the user directly.
Do not generate conversational replies.
Do not make booking decisions.
Only return valid JSON.

The chatbot supports these intents:
- ticket: user wants to search for train tickets
- delay: user wants to predict or report a train delay
- faq: user asks a general railway or ticketing question
- unknown: intent is unclear

Extract the following fields when they are present.
Use null for missing values.

Required JSON schema:
{{
  "intent": "ticket | delay | faq | unknown",
  "from_station": null,
  "to_station": null,
  "journey_type": "single | return | null",
  "depart_date": null,
  "depart_time_pref": null,
  "return_date": null,
  "return_time_pref": null,
  "train_id": null,
  "current_station": null,
  "delay_minutes": null,
  "destination": null,
  "confidence": 0.0
}}

Rules:
- Return only JSON. Do not include explanations or markdown.
- Use ISO format for dates where possible, for example "2026-07-15".
- Convert delay durations into minutes, for example "1 hour 15 minutes" becomes 75.
- If a station is unclear, return the raw phrase rather than guessing.
- If the message contains both ticket and delay information, choose the stronger intent.
- Use the current state to fill context only when the user message clearly refers to it.
- Confidence must be a number between 0 and 1.

User message:
{text}

Current conversation state:
{current_state}
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