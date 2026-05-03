class DelayPredictionAdapter:
    """
    Placeholder adapter for Task 2 prediction model.

    replace this logic with a trained model.
    can collect structured delay information and pass 
    it to a prediction component.
    """

    def predict_arrival(self, delay_dict: dict) -> dict:
        train_id = delay_dict.get("train_id")
        current_station = delay_dict.get("current_station")
        delay_minutes = delay_dict.get("delay_minutes")
        destination = delay_dict.get("destination")

        return {
            "status": "placeholder",
            "message": (
                f"Delay details received for train/service {train_id}.\n"
                f"Current station: {current_station}\n"
                f"Current delay: {delay_minutes} minutes\n"
                f"Destination: {destination}\n\n"
                "The trained prediction model will later use these values "
                "to estimate the arrival time."
            ),
            "input": delay_dict
        }