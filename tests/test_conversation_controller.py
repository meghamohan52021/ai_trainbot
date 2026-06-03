from unittest.mock import patch

from controller import ConversationController


def test_greeting_should_not_go_to_kb():
    bot = ConversationController()
    response = bot.handle_user_input("hi")
    assert "ticket" in response.lower() or "help" in response.lower()


def test_ticket_flow_destination_first():
    bot = ConversationController()

    response = bot.handle_user_input("i want to go to norwich")

    assert "travelling from" in response.lower()
    assert bot.state.current_task == "ticket"
    assert bot.state.ticket.to_station == "NORWICH"


def test_ticket_flow_origin_after_destination():
    bot = ConversationController()

    bot.handle_user_input("i want to go to norwich")
    response = bot.handle_user_input("london liverpool")

    assert bot.state.ticket.from_station == "LIVERPOOL STREET LONDON"
    assert "single or return" in response.lower()


def test_ticket_flow_single_journey():
    bot = ConversationController()

    bot.handle_user_input("i want to go to norwich")
    bot.handle_user_input("london liverpool")
    response = bot.handle_user_input("single")

    assert bot.state.ticket.journey_type == "single"
    assert "date" in response.lower()


def test_ticket_flow_time_and_summary():
    bot = ConversationController()

    bot.handle_user_input("i want to go to norwich")
    bot.handle_user_input("london liverpool")
    bot.handle_user_input("single")
    bot.handle_user_input("next friday")
    response = bot.handle_user_input("morning")

    assert "journey summary" in response.lower()
    assert "norwich" in response.lower()
    assert "liverpool street london" in response.lower()


@patch("controller.TicketSearchAdapter.search_cheapest")
def test_ticket_confirmation_calls_ticket_adapter(mock_search):
    mock_search.return_value = {"message": "Cheapest ticket found: £20"}

    bot = ConversationController()
    bot.handle_user_input("i want to go to norwich")
    bot.handle_user_input("london liverpool")
    bot.handle_user_input("single")
    bot.handle_user_input("next friday")
    bot.handle_user_input("morning")

    response = bot.handle_user_input("yes")

    assert "Cheapest ticket found" in response
    mock_search.assert_called_once()