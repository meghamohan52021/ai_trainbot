import sys
from pathlib import Path
from nlp.station_data import STATION_CODES
from adapters.delay_repay import check_delay_repay

_DELAY_DIR = Path(__file__).parent / "delay_prediction"
if _DELAY_DIR.exists() and str(_DELAY_DIR) not in sys.path:
    sys.path.insert(0, str(_DELAY_DIR))


class DelayPredictionAdapter:
    # This adapter serves as a bridge between the controller and the delay prediction component

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

            # Check Delay Repay eligibility
            operator = "South Western Railway"  # default for Weymouth-Waterloo route
            delay_repay_msg = check_delay_repay(predicted_delay, operator)

            return {
                "status": "ok",
                "message": (
                    f"Current station: {current_station} ({current_crs})<br>"
                    f"Current delay: {delay_minutes} minutes<br>"
                    f"Destination: {destination} ({destination_crs})<br><br>"
                    f"<b>Predicted arrival time: {predicted_time}</b><br>"
                    f"Predicted final delay: {predicted_delay} minutes"
                    f"{delay_repay_msg}"
                ),
                "input": delay_dict,
                "prediction": result,
            }

        except FileNotFoundError:
            # Model not trained yet - still show delay repay based on current delay
            delay_repay_msg = check_delay_repay(delay_minutes, "South Western Railway")

            return {
                "status": "error",
                "message": (
                    f"Current station: {current_station} ({current_crs})<br>"
                    f"Current delay: {delay_minutes} minutes<br>"
                    f"Destination: {destination} ({destination_crs})<br><br>"
                    f"<b>Note:</b> The trained delay prediction model is not available. "
                    f"Showing Delay Repay guidance based on your current delay."
                    f"{delay_repay_msg}"
                ),
                "input": delay_dict,
            }

        except Exception as exc:
            return {
                "status": "error",
                "message": f"The delay prediction component returned an error: {exc}",
                "input": delay_dict,
            }