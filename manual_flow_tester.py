from __future__ import annotations

import argparse
import sys
import traceback
from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional

from controller import ConversationController


@dataclass
class Scenario:
    name: str
    inputs: List[str]
    expected_contains: Optional[List[str]] = None


def patch_adapters(bot: ConversationController) -> None:

    def fake_ticket_search(journey: dict):
        return {
            "message": (
                "[MOCK TICKET ADAPTER]\n"
                f"From: {journey.get('from_station')}\n"
                f"To: {journey.get('to_station')}\n"
                f"Type: {journey.get('journey_type')}\n"
                f"Depart date: {journey.get('depart_date')}\n"
                f"Depart time: {journey.get('depart_time_pref')}\n"
                f"Return date: {journey.get('return_date')}\n"
                f"Return time: {journey.get('return_time_pref')}\n"
                "Cheapest ticket found: £20.00"
            )
        }

    def fake_delay_prediction(delay_data: dict):
        return {
            "message": (
                "[MOCK DELAY ADAPTER]\n"
                f"Current station: {delay_data.get('current_station')}\n"
                f"Current delay: {delay_data.get('delay_minutes')} minutes\n"
                f"Destination: {delay_data.get('destination')}\n\n"
                "Predicted arrival time: 13:01\n"
                "Predicted final delay: 16.6 minutes\n"
                "Model used: Gradient Boosting"
            )
        }

    bot.ticket_search.search_cheapest = fake_ticket_search
    bot.delay_predictor.predict_arrival = fake_delay_prediction


def run_scenario(scenario: Scenario, real_adapters: bool = False) -> bool:
    """
    Runs one full conversation scenario and prints the transcript
    Returns True if the scenario completed without exceptions and the expected
    phrases were present.
    """
    print("\n")
    print(f"SCENARIO: {scenario.name}")

    bot = ConversationController()

    if not real_adapters:
        patch_adapters(bot)

    print("Bot:", bot.prompts.greeting())

    transcript_text = []

    try:
        for user_input in scenario.inputs:
            print(f"\nYou: {user_input}")
            response = bot.handle_user_input(user_input)
            print(f"Bot: {response}")
            transcript_text.append(f"You: {user_input}\nBot: {response}")

        transcript_joined = "\n".join(transcript_text).lower()

        missing = []
        for expected in scenario.expected_contains or []:
            if expected.lower() not in transcript_joined:
                missing.append(expected)

        if missing:
            print("\nRESULT: CHECK MANUALLY")
            print("Reason: These expected phrases were not found:")
            for item in missing:
                print(f"  - {item}")
            return False

        print("\nRESULT: PASS")
        return True

    except Exception:
        print("\nRESULT: ERROR")
        traceback.print_exc()
        return False


def build_scenarios() -> List[Scenario]:

    return [
        Scenario(
            name="00 greeting should not trigger random KB answer",
            inputs=[
                "hi",
            ],
            expected_contains=[
                "help",
                "ticket",
            ],
        ),

        Scenario(
            name="01 basic ticket flow - destination first",
            inputs=[
                "i want to go to norwich",
                "london liverpool",
                "single",
                "next friday",
                "morning",
                "yes",
            ],
            expected_contains=[
                "Where are you travelling from",
                "LIVERPOOL STREET LONDON",
                "NORWICH",
                "journey summary",
                "MOCK TICKET ADAPTER",
            ],
        ),

        Scenario(
            name="02 ticket flow - spelling mistake destination",
            inputs=[
                "i want to go to norwicch",
                "london liverpool",
                "single",
                "tomorrow",
                "after 2pm",
                "yes",
            ],
            expected_contains=[
                "NORWICH",
                "journey summary",
            ],
        ),

        Scenario(
            name="03 ticket flow - full sentence with date and time",
            inputs=[
                "i need a cheap ticket from london liverpool to norwich tomorrow 3pm",
                "single",
                "yes",
            ],
            expected_contains=[
                "LIVERPOOL STREET LONDON",
                "NORWICH",
                "At 15:00",
                "MOCK TICKET ADAPTER",
            ],
        ),

        Scenario(
            name="04 return ticket flow with return time correction",
            inputs=[
                "i want to go to kings cross from norwich",
                "return",
                "tomorrow 3pm",
                "day after tomorrow",
                "return time 11am",
                "yes",
            ],
            expected_contains=[
                "KING'S CROSS LONDON",
                "NORWICH",
                "Return time",
                "11:00",
                "MOCK TICKET ADAPTER",
            ],
        ),

        Scenario(
            name="05 ticket flow - ambiguous London input then corrected",
            inputs=[
                "i want to go to norwich",
                "london",
                "london liverpool",
                "single",
                "next friday",
                "morning",
            ],
            expected_contains=[
                "several matching stations",
                "single or return",
                "journey summary",
            ],
        ),

        Scenario(
            name="06 ticket flow - invalid station / country-like input",
            inputs=[
                "i want to go to norway",
            ],
            expected_contains=[
                "could not find",
            ],
        ),

        Scenario(
            name="07 mixed ticket + delay sentence should choose delay flow",
            inputs=[
                "i want to go to norwich but my train got delayed",
                "Southampton Central",
                "15 mins",
                "Waterloo London",
                "yes",
            ],
            expected_contains=[
                "currently reached",
                "delay information",
                "MOCK DELAY ADAPTER",
            ],
        ),

        Scenario(
            name="08 delay flow standard model route",
            inputs=[
                "my train got delayed",
                "Southampton Central",
                "15 mins",
                "Waterloo London",
                "yes",
            ],
            expected_contains=[
                "SOUTHAMPTON CENTRAL",
                "15 minutes",
                "WATERLOO LONDON",
                "Predicted final delay",
            ],
        ),

        Scenario(
            name="09 delay flow - one hour conversion",
            inputs=[
                "my train is delayed",
                "Southampton Central",
                "1 hour",
                "Waterloo London",
                "yes",
            ],
            expected_contains=[
                "Delay: 60 minutes",
                "Predicted arrival time",
            ],
        ),

        Scenario(
            name="10 delay flow - spelling mistake in delay word",
            inputs=[
                "my train is dalayyyed",
                "Southampton Central",
                "10 mins",
                "Waterloo London",
                "yes",
            ],
            expected_contains=[
                "currently reached",
                "Predicted final delay",
            ],
        ),

        Scenario(
            name="11 delay flow - station ambiguity then choose full station",
            inputs=[
                "my train got delayed",
                "southampton",
                "SOUTHAMPTON CENTRAL",
                "15 mins",
                "waterloo",
                "WATERLOO LONDON",
                "yes",
            ],
            expected_contains=[
                "several matching stations",
                "SOUTHAMPTON CENTRAL",
                "WATERLOO LONDON",
                "Predicted arrival time",
            ],
        ),

        Scenario(
            name="12 correction after delay summary",
            inputs=[
                "my train got delayed",
                "Southampton Central",
                "15 mins",
                "Waterloo London",
                "no",
                "delay",
                "1 hour",
                "yes",
            ],
            expected_contains=[
                "What needs changing",
                "60 minutes",
                "Predicted final delay",
            ],
        ),

        Scenario(
            name="13 knowledge base exact FAQ",
            inputs=[
                "what is delay repay?",
            ],
            expected_contains=[
                "delay",
            ],
        ),

        Scenario(
            name="14 reset clears previous flow",
            inputs=[
                "i want to go to norwich",
                "reset",
                "my train got delayed",
            ],
            expected_contains=[
                "Conversation reset",
                "currently reached",
            ],
        ),

        Scenario(
            name="15 goodbye ends conversation politely",
            inputs=[
                "bye",
            ],
            expected_contains=[
                "safe travels",
            ],
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--real-adapters",
        action="store_true",
        help="Call the real ticket API and delay model instead of mock adapters.",
    )
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="Run only scenarios whose name contains this text, e.g. --only delay",
    )
    args = parser.parse_args()

    scenarios = build_scenarios()

    if args.only:
        scenarios = [s for s in scenarios if args.only.lower() in s.name.lower()]

    print("TrainBot scripted flow tester")
    print(f"Total scenarios: {len(scenarios)}")
    print(f"Adapters: {'REAL' if args.real_adapters else 'MOCK'}")

    passed = 0
    failed = 0

    for scenario in scenarios:
        ok = run_scenario(scenario, real_adapters=args.real_adapters)
        if ok:
            passed += 1
        else:
            failed += 1

    print("SUMMAR\nY")
    print(f"Passed: {passed}")
    print(f"Failed / check manually: {failed}")
    print(f"Total: {passed + failed}")

    if failed:
        print("\nSome scenarios need checking. Copy the full output and inspect the failed sections.")
        return 1

    print("\nAll scripted flows passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
