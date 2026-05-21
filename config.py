from datetime import datetime
from zoneinfo import ZoneInfo

TIMEZONE = "Europe/London"

INTENT_HIGH_CONFIDENCE = 0.80
INTENT_MEDIUM_CONFIDENCE = 0.50
KB_MATCH_THRESHOLD = 0.45
FUZZY_STATION_THRESHOLD = 85

def now_london():
    return datetime.now(ZoneInfo(TIMEZONE))