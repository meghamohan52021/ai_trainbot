import sys
from pathlib import Path
from datetime import datetime, timedelta
from station_data import STATION_CODES

_DELAY_DIR = Path(__file__).parent / "delay_prediction"
if _DELAY_DIR.exists() and str(_DELAY_DIR) not in sys.path:
    sys.path.insert(0, str(_DELAY_DIR))


class DelayPredictionAdapter:
    #This adapter serves as a bridge between the controller and the delay prediction component

    def _resolve_crs(self, station):
        if not station:
            return None
        value = str(station).strip()
        if len(value) == 3 and value.isalpha():
            return value.upper()
        return STATION_CODES.get(value)


    def predict_arrival(self, delay_dict: dict) -> dict:
        current_station = delay_dict.get("current_station")
        delay_minutes = delay_dict.get("delay_minutes")
        destination = delay_dict.get("destination")

        current_crs = self._resolve_crs(current_station)
        destination_crs = self._resolve_crs(destination)

        if not current_crs:
            return {
                "status": "error",
                "message": f"Sorry, I could not recognise '{current_station}' as a station.",
                "input": delay_dict,
            }

        if not destination_crs:
            return {
                "status": "error",
                "message": f"Sorry, I could not recognise '{destination}' as a destination station.",
                "input": delay_dict,
            }

        try:
            delay_minutes = int(delay_minutes)
        except (TypeError, ValueError):
            return {
                "status": "error",
                "message": "Delay minutes must be a number, for example 10.",
                "input": delay_dict,
            }

        try:
            from delay_prediction.predict import predict_arrival

            result = predict_arrival(
                current_station=current_crs,
                delay_minutes=float(delay_minutes),
                destination=destination_crs,
            )

            predicted_time = result.get("predicted_arrival_time", "unknown")
            predicted_delay = result.get("predicted_delay_minutes", "unknown")
            return {
                "status": "ok",
                "message": (
                    f"Current station: {current_station} ({current_crs})\n"
                    f"Current delay: {delay_minutes} minutes\n"
                    f"Destination: {destination} ({destination_crs})\n\n"
                    f"Predicted arrival time: {predicted_time}\n"
                    f"Predicted final delay: {predicted_delay} minutes"
                ),
                "input": delay_dict,
                "prediction": result,
            }

        except FileNotFoundError:
            return {
                "status": "error",
                "message": (
                "The trained delay prediction model is not available.\n\n"
                "Please check that these files exist:\n"
                "delay_prediction/models/champion_WEY2WAT.joblib\n"
                "delay_prediction/models/champion_WAT2WEY.joblib\n\n"
                "Run delay_prediction/train.py or add the trained model files before using delay prediction."
                ),}
        except Exception as exc:
            return {
                "status": "error",
                "message": f"The delay prediction component returned an error: {exc}",
                "input": delay_dict,
            }
