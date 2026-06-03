from unittest.mock import patch

from controller import ConversationController


def test_delay_flow_starts_correctly():
    bot = ConversationController()

    response = bot.handle_user_input("my train got delayed")

    assert bot.state.current_task == "delay"
    assert "currently reached" in response.lower()


def test_delay_flow_current_station():
    bot = ConversationController()

    bot.handle_user_input("my train got delayed")
    response = bot.handle_user_input("Southampton Central")

    assert bot.state.delay.current_station == "SOUTHAMPTON CENTRAL"
    assert "how many minutes" in response.lower()


def test_delay_flow_one_hour_converts_to_60():
    bot = ConversationController()

    bot.handle_user_input("my train got delayed")
    bot.handle_user_input("Southampton Central")
    response = bot.handle_user_input("1 hour")

    assert bot.state.delay.delay_minutes == 60
    assert "destination" in response.lower()


def test_delay_flow_destination_and_summary():
    bot = ConversationController()

    bot.handle_user_input("my train got delayed")
    bot.handle_user_input("Southampton Central")
    bot.handle_user_input("15 mins")
    response = bot.handle_user_input("Waterloo London")

    assert bot.state.delay.destination == "WATERLOO LONDON"
    assert "delay information" in response.lower()
    assert "15 minutes" in response.lower()


@patch("controller.DelayPredictionAdapter.predict_arrival")
def test_delay_confirmation_calls_prediction_adapter(mock_predict):
    mock_predict.return_value = {
        "message": (
            "Current station: SOUTHAMPTON CENTRAL (SOU)\n"
            "Current delay: 15 minutes\n"
            "Destination: WATERLOO LONDON (WAT)\n\n"
            "Predicted arrival time: 13:01\n"
            "Predicted final delay: 16.6 minutes"
        )
    }

    bot = ConversationController()
    bot.handle_user_input("my train got delayed")
    bot.handle_user_input("Southampton Central")
    bot.handle_user_input("15 mins")
    bot.handle_user_input("Waterloo London")

    response = bot.handle_user_input("yes")

    assert "Predicted arrival time" in response
    assert "16.6" in response
    mock_predict.assert_called_once()