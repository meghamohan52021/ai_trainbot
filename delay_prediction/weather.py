from pathlib import Path
import pandas as pd

# coordinates for southampton, middle of the wey-wat route
LAT, LON = 50.9099, -1.4044
CACHE_PATH = Path(__file__).parent / "data/interim/weather.parquet"

_HIST = (
    "https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
    "&start_date={start}&end_date={end}"
    "&hourly=temperature_2m,precipitation,windspeed_10m&timezone=Europe%2FLondon"
)
_NOW = (
    "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
    "&current=temperature_2m,precipitation,windspeed_10m&timezone=Europe%2FLondon"
)


def fetch_history(start="2022-01-01", end="2025-12-31", path=CACHE_PATH):
    # return cached version if we already have it
    if path.exists():
        return pd.read_parquet(path)

    import urllib.request, json
    print("Downloading weather history from Open-Meteo...")
    with urllib.request.urlopen(_HIST.format(lat=LAT, lon=LON, start=start, end=end)) as r:
        h = json.load(r)["hourly"]

    times = pd.to_datetime(h["time"])
    df = pd.DataFrame({
        "date": times.strftime("%Y-%m-%d"),
        "hour": times.hour.astype("int8"),
        "temperature": h["temperature_2m"],
        "precipitation": h["precipitation"],
        "windspeed": h["windspeed_10m"],
    })
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    print(f"  Saved {len(df):,} rows -> {path}")
    return df


def current_weather():
    # called at inference time to get live conditions
    import urllib.request, json
    with urllib.request.urlopen(_NOW.format(lat=LAT, lon=LON)) as r:
        c = json.load(r)["current"]
    return {
        "temperature": c["temperature_2m"],
        "precipitation": c["precipitation"],
        "windspeed": c["windspeed_10m"],
    }


if __name__ == "__main__":
    df = fetch_history()
    print(df.head())
    print(f"Rows: {len(df):,}  Date range: {df['date'].min()} -> {df['date'].max()}")
