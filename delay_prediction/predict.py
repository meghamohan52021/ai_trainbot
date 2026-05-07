from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path
import joblib
import pandas as pd

_MODELS_DIR = Path(__file__).parent / "models"
_cache: dict = {}


def _load_model(direction: str = "WEY2WAT"):
    if direction not in _cache:
        path = _MODELS_DIR / f"champion_{direction}.joblib"
        if not path.exists():
            # fallback to old single-model file for backwards compatibility
            path = _MODELS_DIR / "champion.joblib"
            if not path.exists():
                raise FileNotFoundError(f"Run train.py first to generate models/champion_{direction}.joblib")
        _cache[direction] = joblib.load(path)
    return _cache[direction]


def predict_arrival(
    current_station: str,
    delay_minutes: float,
    destination: str = "WAT",
    now: datetime | None = None,
    first_delay: float | None = None,
) -> dict:
    direction = "WAT2WEY" if destination == "WEY" else "WEY2WAT"
    data = _load_model(direction)
    now = now or datetime.now()

    if current_station not in data["route_info"].index:
        raise ValueError(
            f"Unknown station '{current_station}'. Known: {sorted(data['route_info'].index.tolist())}"
        )

    if first_delay is None:
        first_delay = data.get("median_first_delay", 0.0)

    temp = precip = wind = 0.0
    try:
        from weather import current_weather
        wx = current_weather()
        temp, precip, wind = wx["temperature"], wx["precipitation"], wx["windspeed"]
    except Exception:
        pass

    ri = data["route_info"].loc[current_station]
    mins_left = float(ri["planned_mins_remaining"])

    X = pd.DataFrame([{
        "delay_min": float(delay_minutes),
        "stations_remaining": ri["stations_remaining"],
        "planned_mins_remaining": mins_left,
        "hour": float(now.hour),
        "day_of_week": float(now.weekday()),
        "is_weekend": float(now.weekday() >= 5),
        "is_peak": float((7 <= now.hour <= 8 or 17 <= now.hour <= 18) and now.weekday() < 5),
        "season": float((now.month % 12) // 3),
        "first_delay": float(first_delay),
        "temperature": temp,
        "precipitation": precip,
        "windspeed": wind,
    }])

    pred = float(data["model"].predict(X)[0])
    planned_arr = now + timedelta(minutes=mins_left - delay_minutes)
    predicted_arr = planned_arr + timedelta(minutes=pred)

    return {
        "predicted_delay_minutes": round(pred, 1),
        "predicted_arrival_time": predicted_arr.strftime("%H:%M"),
        "model_used": data["name"],
    }
