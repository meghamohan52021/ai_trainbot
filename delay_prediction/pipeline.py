from pathlib import Path
import pandas as pd
import numpy as np

BASE      = Path(__file__).parent
INTERIM   = BASE / "data/interim"
PROCESSED = BASE / "data/processed"
RAW       = BASE / "data/raw"

DEST   = {"WEY2WAT": "WAT", "WAT2WEY": "WEY"}
ORIGIN = {"WEY2WAT": "WEY", "WAT2WEY": "WAT"}

TIME_COLS = [
    "planned_arrival_time", "planned_departure_time",
    "actual_arrival_time",  "actual_departure_time"
]

FEATURES = [
    "delay_min", "stations_remaining", "planned_mins_remaining",
    "hour", "day_of_week", "is_weekend", "is_peak", "season",
    "first_delay", "temperature", "precipitation", "windspeed"
]


def load_raw(direction="WEY2WAT"):
    files = sorted(INTERIM.glob(f"*_{direction}.parquet"))
    if files:
        return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)

    files = sorted(PROCESSED.glob(f"*_{direction}.parquet"))
    if files:
        df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
        for c in TIME_COLS:
            df[c] = df[c].apply(lambda x: np.nan if x is None else x.hour * 60 + x.minute + x.second / 60)
        return df

    # slow path - read from raw xlsx files
    df = pd.concat(
        [pd.read_excel(f) for f in sorted(RAW.glob(f"*_{direction}.xlsx"))],
        ignore_index=True
    )
    for c in TIME_COLS:
        df[c] = pd.to_timedelta(df[c].astype(str), errors="coerce").dt.total_seconds() / 60
    return df


def _add_weather(stops):
    cache = INTERIM / "weather.parquet"
    if not cache.exists():
        for col in ["temperature", "precipitation", "windspeed"]:
            stops[col] = 0.0
        return stops

    wx = pd.read_parquet(cache)
    stops["d"] = pd.to_datetime(stops["date_of_service"]).dt.strftime("%Y-%m-%d")
    stops["h"] = stops["hour"].astype(int)
    stops = stops.merge(
        wx.rename(columns={"date": "d", "hour": "h"}),
        on=["d", "h"], how="left"
    ).drop(columns=["d", "h"])

    for col in ["temperature", "precipitation", "windspeed"]:
        stops[col] = stops[col].fillna(stops[col].median())
    return stops


def make_dataset(direction="WEY2WAT"):
    df   = load_raw(direction)
    dest = DEST[direction]

    df["delay_min"] = df["actual_arrival_time"] - df["planned_arrival_time"]
    missing = df["delay_min"].isna()
    df.loc[missing, "delay_min"] = (
        df.loc[missing, "actual_departure_time"] - df.loc[missing, "planned_departure_time"]
    )

    sort_key = df["planned_arrival_time"].fillna(df["planned_departure_time"])
    df = df.assign(_t=sort_key).sort_values(["rid", "_t"]).drop(columns="_t").reset_index(drop=True)
    df["stop_idx"] = df.groupby("rid").cumcount()

    terminal = (
        df[df["location"] == dest][["rid", "delay_min", "planned_arrival_time"]]
        .rename(columns={"delay_min": "target", "planned_arrival_time": "dest_planned_arr"})
        .dropna(subset=["target"])
        .query("-10 <= target <= 240")
    )

    origin_delay = (
        df[df["location"] == ORIGIN[direction]][["rid", "delay_min"]]
        .drop_duplicates("rid")
        .set_index("rid")["delay_min"]
        .rename("first_delay")
    )

    stops    = df[df["location"] != dest].merge(terminal, on="rid")
    max_idx  = df.groupby("rid")["stop_idx"].max().rename("max_idx")
    stops    = stops.join(max_idx, on="rid")
    stops["stations_remaining"] = stops["max_idx"] - stops["stop_idx"]

    curr = stops["planned_arrival_time"].fillna(stops["planned_departure_time"])
    stops["planned_mins_remaining"] = stops["dest_planned_arr"] - curr
    stops.loc[stops["planned_mins_remaining"] < 0, "planned_mins_remaining"] += 1440

    stops["hour"]        = (curr // 60) % 24
    stops["day_of_week"] = pd.to_datetime(stops["date_of_service"]).dt.dayofweek
    stops["is_weekend"]  = (stops["day_of_week"] >= 5).astype(int)
    stops["is_peak"]     = (
        (stops["hour"].between(7, 8) | stops["hour"].between(17, 18)) & (stops["day_of_week"] < 5)
    ).astype(int)

    month          = pd.to_datetime(stops["date_of_service"]).dt.month
    stops["season"] = ((month % 12) // 3).astype(int)

    stops = stops.join(origin_delay, on="rid")
    stops["first_delay"] = stops["first_delay"].fillna(0.0)
    stops = _add_weather(stops)

    route_info = stops.groupby("location")[["stations_remaining", "planned_mins_remaining"]].median().round(1)
    valid      = stops[FEATURES + ["target", "date_of_service"]].dropna(subset=FEATURES + ["target"])
    return valid[FEATURES], valid["target"], route_info, valid["date_of_service"]
