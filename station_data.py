import csv
from pathlib import Path

STATION_ALIASES = {}
STATION_CODES = {}  # canonical station name -> CRS code


def load_station_data():
    global STATION_ALIASES, STATION_CODES

    csv_path = Path(__file__).parent / "StationNameAndCode.csv"

    try:
        with open(csv_path, newline="", encoding="utf-8") as file:
            reader = csv.reader(file)

            next(reader)  #skip header

            for row in reader:
                if len(row) < 2:
                    continue

                station_name = row[0].strip()
                code = row[1].strip()

                if station_name:
                    STATION_ALIASES[station_name.lower()] = station_name
                    if code:
                        STATION_CODES[station_name] = code

                if code:
                    STATION_ALIASES[code.lower()] = station_name

    except FileNotFoundError:
        print("Station CSV not found.")


load_station_data()

VALID_STATIONS = set(STATION_ALIASES.values())