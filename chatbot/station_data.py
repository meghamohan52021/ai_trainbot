import csv

STATION_ALIASES = {}


def load_station_data():
    global STATION_ALIASES

    try:
        with open("StationNameAndCode.csv", newline="", encoding="utf-8") as file:
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
                    STATION_ALIASES[code.lower()] = station_name

    except FileNotFoundError:
        print("Station CSV not found.")


load_station_data()