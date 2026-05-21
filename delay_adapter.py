import sys
from pathlib import Path

_DP_DIR = Path(__file__).parent / "delay_prediction"
if str(_DP_DIR) not in sys.path:
    sys.path.insert(0, str(_DP_DIR))

from station_data import STATION_CODES


class DelayPredictionAdapter:
    def _resolve_crs(self, station):
        if not station:
            return None
        s = station.strip()
        # already a CRS code
        if len(s) == 3 and s.isalpha():
            return s.upper()
        return STATION_CODES.get(s)

    def predict_arrival(self, delay_dict: dict) -> dict:
        train_id      = delay_dict.get("train_id")
        cur_station   = delay_dict.get("current_station")
        delay_mins    = delay_dict.get("delay_minutes")
        dest          = delay_dict.get("destination")

        cur_crs  = self._resolve_crs(cur_station)
        dest_crs = self._resolve_crs(dest) or "WAT"

        if not cur_crs:
            return {
                "status": "error",
                "message": f"Sorry, I couldn't recognise '{cur_station}' as a station on the Weymouth-London Waterloo route.",
                "input": delay_dict,
            }

        try:
            from delay_prediction.predict import predict_arrival
            result = predict_arrival(
                current_station=cur_crs,
                delay_minutes=float(delay_mins or 0),
                destination=dest_crs,
            )
        except FileNotFoundError:
            return {
                "status": "model_missing",
                "message": (
                    "The delay prediction model hasn't been trained yet. "
                    "Run `python delay_prediction/train.py` to generate "
                    "delay_prediction/models/champion.joblib, then try again."
                ),
                "input": delay_dict,
            }
        except ValueError as e:
            return {
                "status": "error",
                "message": f"Couldn't predict for '{cur_station}' ({cur_crs}): {e}",
                "input": delay_dict,
            }

        return {
            "status": "ok",
            "message": (
                f"Train/service {train_id} at {cur_station} ({cur_crs}) "
                f"with a {int(delay_mins)}-minute delay.\n"
                f"Predicted arrival at {dest}: "
                f"{result['predicted_arrival_time']} "
                f"(predicted final delay: {result['predicted_delay_minutes']} min, "
            ),
            "input": delay_dict,
            "prediction": result,
        }
