from datetime import datetime
from zoneinfo import ZoneInfo
import os

# General settings
TIMEZONE = "Europe/London"

# NLU thresholds
INTENT_HIGH_CONFIDENCE = 0.80
INTENT_MEDIUM_CONFIDENCE = 0.50
KB_MATCH_THRESHOLD = 0.45
FUZZY_STATION_THRESHOLD = 85


def now_london():
    return datetime.now(ZoneInfo(TIMEZONE))


# Gemini fallback settings
GEMINI_API_KEY = "AIzaSyCXE7wdvPhdT1Ix2hckPLnsda6a6eMN-E8"
GEMINI_MODEL = "gemini-2.5-flash"

GEMINI_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/"
    f"models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)

#fallback switch
USE_LLM_FALLBACK = True

LLM_DEBUG = True

SHOW_LLM_TO_USER = True
