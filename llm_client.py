import json
import re
import requests

try:
    from config import (
        GEMINI_API_KEY,
        GEMINI_MODEL,
        GEMINI_API_URL,
        USE_LLM_FALLBACK,
        LLM_DEBUG,
    )
except Exception:
    GEMINI_API_KEY = ""
    GEMINI_MODEL = "gemini-flash-latest"
    GEMINI_API_URL = ""
    USE_LLM_FALLBACK = False
    LLM_DEBUG = False


class LLMClient:
    #Controlled Gemini fallback parser for structured data extraction when local NLU is unsure.

    #It does not generate final user-facing chatbot answers

    def __init__(self):
        self.enabled = bool(USE_LLM_FALLBACK)
        self.api_key = GEMINI_API_KEY
        self.model = GEMINI_MODEL
        self.api_url = GEMINI_API_URL

    def extract_structured_data(self, text: str, current_state: dict | None = None, local_context: dict | None = None) -> dict:
        if not self.enabled:
            self._debug("[LLM FALLBACK] Disabled in config.py.")
            return {}

        if not self.api_key or "PASTE_YOUR" in self.api_key:
            self._debug("[LLM FALLBACK] Missing Gemini API key in config.py.")
            return {}

        if not self.api_url:
            self._debug("[LLM FALLBACK] Missing GEMINI_API_URL in config.py.")
            return {}

        current_state = current_state or {}
        local_context = local_context or {}
        prompt = self._build_prompt(text, current_state, local_context)

        if LLM_DEBUG:
            print("\n" + "=" * 90)
            print("[LLM FALLBACK] Gemini is being used as a final structured NLU attempt.")
            print(f"[LLM FALLBACK] Model: {self.model}")
            print("[LLM FALLBACK] URL:", self._safe_url())
            print("[LLM FALLBACK] Prompt sent to Gemini:")
            print(prompt)
            print("=" * 90 + "\n")

        #Gemini REST API expects camelCase names, e.g. responseMimeType, not response_mime_type
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt}
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "topP": 0.1,
                "maxOutputTokens": 2048,
                "responseMimeType": "application/json",
            },
        }

        try:
            response = requests.post(
                self.api_url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=25,
            )
            response.raise_for_status()
            data = response.json()

            if LLM_DEBUG:
                self._print_gemini_debug_metadata(data)

            raw_text = self._extract_text_from_gemini_response(data)
            raw_text = self._clean_json_text(raw_text)

            if LLM_DEBUG:
                print("\n[LLM FALLBACK] Raw Gemini response:")
                print(raw_text)
                print("-" * 90)

            parsed = self._parse_json_safely(raw_text)
            parsed = self._normalise_result(parsed)
            parsed["_llm_used"] = True
            parsed["_llm_model"] = self.model

            if LLM_DEBUG:
                print("\n[LLM FALLBACK] Parsed Gemini JSON:")
                print(json.dumps(parsed, indent=2))
                print("-" * 90 + "\n")

            return parsed

        except Exception as exc:
            if LLM_DEBUG:
                print("\n[LLM FALLBACK] Gemini fallback failed.")
                print(f"[LLM FALLBACK] Error: {exc}")
                print("-" * 90 + "\n")
            return {}

    def _build_prompt(self, text: str, current_state: dict, local_context: dict) -> str:
        return f"""
You are a strict JSON extractor for a UK train chatbot.

Return ONE valid JSON object only. No markdown. No explanation. No extra text.
Do not answer the user. Do not call APIs. Do not invent ticket prices.

Allowed intent values: ticket, delay, faq, unknown.
Allowed journey_type values: single, return, null.

JSON keys required exactly:
intent, from_station, to_station, journey_type, depart_date, depart_time_pref,
return_date, return_time_pref, train_id, current_station, delay_minutes,
destination, confidence

Rules:
- Use null for missing values.
- Station values should be the raw station phrase from the user.
- If the user gives a relative date like tomorrow, keep it as "tomorrow".
- Time preferences can be simple phrases: morning, afternoon, before 10am, after 2pm, any time.
- Convert written delay durations to minutes, e.g. fifteen minutes -> 15.
- confidence must be a number from 0 to 1.

Current state:
{json.dumps(current_state, default=str)}

Local NLU context:
{json.dumps(local_context, default=str)}

User message:
{text}
""".strip()

    def _extract_text_from_gemini_response(self, data: dict) -> str:
        candidates = data.get("candidates") or []
        if not candidates:
            raise ValueError(f"Gemini response has no candidates: {data}")

        content = candidates[0].get("content") or {}
        parts = content.get("parts") or []
        if not parts:
            raise ValueError(f"Gemini response has no content parts: {data}")

        text_chunks = []
        for part in parts:
            if isinstance(part, dict) and part.get("text"):
                text_chunks.append(part["text"])

        full_text = "".join(text_chunks).strip()
        if not full_text:
            raise ValueError(f"Gemini response text is empty: {data}")

        return full_text

    def _clean_json_text(self, raw_text: str) -> str:
        cleaned = (raw_text or "").strip()

        if cleaned.startswith("```json"):
            cleaned = cleaned[len("```json"):].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned[len("```"):].strip()

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

        return cleaned

    def _parse_json_safely(self, raw_text: str) -> dict:
        try:
            parsed = json.loads(raw_text)
            if isinstance(parsed, dict):
                return parsed
            raise ValueError("Gemini JSON root was not an object/dict.")
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
            if not match:
                raise
            parsed = json.loads(match.group(0))
            if not isinstance(parsed, dict):
                raise ValueError("Recovered Gemini JSON root was not an object/dict.")
            return parsed

    def _normalise_result(self, parsed: dict) -> dict:
        allowed_intents = {"ticket", "delay", "faq", "unknown"}
        result = {
            "intent": parsed.get("intent"),
            "from_station": parsed.get("from_station"),
            "to_station": parsed.get("to_station"),
            "journey_type": parsed.get("journey_type"),
            "depart_date": parsed.get("depart_date"),
            "depart_time_pref": parsed.get("depart_time_pref"),
            "return_date": parsed.get("return_date"),
            "return_time_pref": parsed.get("return_time_pref"),
            "train_id": parsed.get("train_id"),
            "current_station": parsed.get("current_station"),
            "delay_minutes": parsed.get("delay_minutes"),
            "destination": parsed.get("destination"),
            "confidence": parsed.get("confidence", 0.0),
        }

        if isinstance(result["intent"], str):
            result["intent"] = result["intent"].lower().strip()
        if result["intent"] not in allowed_intents:
            result["intent"] = "unknown"

        if isinstance(result["journey_type"], str):
            result["journey_type"] = result["journey_type"].lower().strip()
        if result["journey_type"] not in {"single", "return", None}:
            result["journey_type"] = None

        try:
            result["confidence"] = float(result["confidence"])
        except (TypeError, ValueError):
            result["confidence"] = 0.0
        result["confidence"] = max(0.0, min(1.0, result["confidence"]))

        if result["delay_minutes"] is not None:
            try:
                result["delay_minutes"] = int(result["delay_minutes"])
            except (TypeError, ValueError):
                result["delay_minutes"] = None

        for key, value in list(result.items()):
            if isinstance(value, str) and not value.strip():
                result[key] = None

        return result

    def _print_gemini_debug_metadata(self, data: dict) -> None:
        candidates = data.get("candidates") or []
        if not candidates:
            print("[LLM FALLBACK] Gemini metadata: no candidates returned")
            return

        candidate = candidates[0]
        print("[LLM FALLBACK] Gemini finishReason:", candidate.get("finishReason"))
        if candidate.get("safetyRatings"):
            print("[LLM FALLBACK] Gemini safetyRatings:", candidate.get("safetyRatings"))
        if data.get("usageMetadata"):
            print("[LLM FALLBACK] Gemini usageMetadata:", data.get("usageMetadata"))

    def _safe_url(self) -> str:
        if not self.api_url:
            return ""
        return self.api_url.replace(self.api_key, "***API_KEY_HIDDEN***")

    def _debug(self, message: str) -> None:
        if LLM_DEBUG:
            print(message)
