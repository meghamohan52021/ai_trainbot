# Delay Repay guidance module
# Checks eligibility based on predicted delay and returns operator claim info

OPERATOR_DELAY_REPAY = {
    "South Western Railway": {
        "threshold_minutes": 15,
        "claim_url": "https://www.southwesternrailway.com/contact-and-help/delay-repay",
        "compensation": "25% for 15-29 mins, 50% for 30-59 mins, 100% for 60+ mins",
    },
    "Greater Anglia": {
        "threshold_minutes": 15,
        "claim_url": "https://www.greateranglia.co.uk/about-us/our-performance/delay-repay",
        "compensation": "25% for 15-29 mins, 50% for 30-59 mins, 100% for 60+ mins",
    },
    "Great Western Railway": {
        "threshold_minutes": 15,
        "claim_url": "https://www.gwr.com/help-and-support/refunds-and-compensation/delay-repay",
        "compensation": "25% for 15-29 mins, 50% for 30-59 mins, 100% for 60+ mins",
    },
    "Avanti West Coast": {
        "threshold_minutes": 15,
        "claim_url": "https://www.avantiwestcoast.co.uk/help-and-support/delay-repay",
        "compensation": "25% for 15-29 mins, 50% for 30-59 mins, 100% for 60+ mins",
    },
    "LNER": {
        "threshold_minutes": 30,  # LNER uses DR30, not DR15
        "claim_url": "https://www.lner.co.uk/support/delay-repay/",
        "compensation": "50% for 30-59 mins, 100% for 60+ mins",
    },
    "Thameslink": {
        "threshold_minutes": 15,
        "claim_url": "https://www.thameslinkrailway.com/help-and-support/delay-repay",
        "compensation": "25% for 15-29 mins, 50% for 30-59 mins, 100% for 60+ mins",
    },
    "Southern": {
        "threshold_minutes": 15,
        "claim_url": "https://www.southernrailway.com/help-and-support/delay-repay",
        "compensation": "25% for 15-29 mins, 50% for 30-59 mins, 100% for 60+ mins",
    },
    "CrossCountry": {
        "threshold_minutes": 15,
        "claim_url": "https://www.crosscountrytrains.co.uk/help-support/delay-repay",
        "compensation": "25% for 15-29 mins, 50% for 30-59 mins, 100% for 60+ mins",
    },
    "TransPennine Express": {
        "threshold_minutes": 15,
        "claim_url": "https://www.tpexpress.co.uk/help/delay-repay-compensation",
        "compensation": "25% for 15-29 mins, 50% for 30-59 mins, 100% for 60+ mins",
    },
    "National Rail": {
        "threshold_minutes": 15,
        "claim_url": "https://www.nationalrail.co.uk/compensation",
        "compensation": "25% for 15-29 mins, 50% for 30-59 mins, 100% for 60+ mins",
    },
}

# Default operator for the Weymouth-Waterloo route
DEFAULT_OPERATOR = "South Western Railway"


def check_delay_repay(predicted_delay, operator: str = None) -> str:
    """
    Checks if the predicted delay qualifies for Delay Repay.
    Returns an HTML guidance message string, or empty string if not eligible.
    """
    try:
        delay = float(predicted_delay)
    except (TypeError, ValueError):
        return ""

    if operator is None:
        operator = DEFAULT_OPERATOR

    # Find matching operator info (case-insensitive partial match)
    operator_info = None
    matched_name = operator
    for key in OPERATOR_DELAY_REPAY:
        if key.lower() in operator.lower() or operator.lower() in key.lower():
            operator_info = OPERATOR_DELAY_REPAY[key]
            matched_name = key
            break

    if operator_info is None:
        operator_info = OPERATOR_DELAY_REPAY["National Rail"]
        matched_name = "National Rail"

    threshold = operator_info["threshold_minutes"]

    if delay < threshold:
        return (
            f"<br><br>Your predicted delay of <b>{delay:.0f} minutes</b> does not currently "
            f"meet the {threshold}-minute threshold for Delay Repay with {matched_name}."
        )

    # Determine compensation rate
    if delay >= 60:
        rate = "100%"
    elif delay >= 30:
        rate = "50%"
    else:
        rate = "25%"

    claim_url = operator_info["claim_url"]

    return (
        f"<br><br><b>Delay Repay Eligibility</b><br>"
        f"Your predicted delay of <b>{delay:.0f} minutes</b> qualifies for Delay Repay "
        f"with {matched_name}.<br>"
        f"You may be entitled to <b>{rate}</b> of your fare back.<br><br>"
        f"To claim, you will need:<br>"
        f"• Your booking reference or ticket<br>"
        f"• Travel date and route<br>"
        f"• Departure and arrival station<br>"
        f"• Your payment method for the refund<br><br>"
        f"<a href='{claim_url}' target='_blank'>Claim Delay Repay with {matched_name} →</a>"
    )