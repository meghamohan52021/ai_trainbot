import requests
import xml.etree.ElementTree as ET
import re

# National Rail KB API credentials
KB_EMAIL = "rishitathummala223@gmail.com"
KB_PASSWORD = "Icecream1199*"  # account password - update if changed

KB_AUTH_URL = "https://opendata.nationalrail.co.uk/authenticate"
KB_INCIDENTS_URL = "https://opendata.nationalrail.co.uk/api/staticfeeds/5.0/incidents"
FALLBACK_URL = "https://www.nationalrail.co.uk/status-and-disruptions/"

# XML namespaces
NS = {
    "inc": "http://nationalrail.co.uk/xml/incident",
    "com": "http://nationalrail.co.uk/xml/common",
}

DISRUPTION_KEYWORDS = {
    "disruption", "disruptions", "delay", "delayed", "delays",
    "problem", "problems", "issue", "issues", "engineering",
    "cancellation", "cancelled", "strike", "service", "services",
    "what's happening", "whats happening", "any problems",
    "network", "status", "running", "normal", "on time",
    "train status", "service update", "live disruptions",
}


def is_disruption_query(text: str) -> bool:
    lower = text.lower().strip().rstrip("?!.")  # strip punctuation
    
    # Single word triggers
    single_triggers = {
        "disruptions", "disruption", "cancellations",
        "incidents", "engineering", "status"
    }
    if lower in single_triggers:
        return True

    phrases = [
        "any disruption", "any problem", "any issue",
        "what's happening", "whats happening", "service disruption",
        "train disruption", "disruptions today", "delays today",
        "network status", "are trains running", "train status",
        "engineering work", "any cancellation", "service update",
        "what is happening", "current disruptions", "live disruptions",
        "disruptions on", "delays on", "problems on",
    ]
    if any(phrase in lower for phrase in phrases):
        return True

    words = set(lower.split())
    return len(words & DISRUPTION_KEYWORDS) >= 2


def _get_token() -> str:
    """Authenticate and return a token."""
    resp = requests.post(
        KB_AUTH_URL,
        json={"username": KB_EMAIL, "password": KB_PASSWORD},
        timeout=10,
    )
    if resp.status_code == 200:
        return resp.json().get("token", "")
    return ""


def _strip_html(text: str) -> str:
    """Remove HTML tags from description text."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def get_disruptions() -> dict:
    """
    Fetches current incidents from the National Rail KB API.
    Returns a formatted message with active disruptions.
    """
    try:
        token = _get_token()
        if not token:
            return _fallback("Could not authenticate with National Rail.")

        resp = requests.get(
            KB_INCIDENTS_URL,
            headers={"X-Auth-Token": token},
            timeout=10,
        )

        if resp.status_code != 200:
            return _fallback(f"API returned status {resp.status_code}.")

        root = ET.fromstring(resp.content)
        incidents = root.findall("inc:PtIncident", NS)

        if not incidents:
            return {
                "status": "ok",
                "message": (
                    "There are currently no reported disruptions on the National Rail network. "
                    "Services appear to be running normally.<br><br>"
                    f"<a href='{FALLBACK_URL}' target='_blank'>Check National Rail status →</a>"
                )
            }

        # Filter to unplanned/active disruptions only (exclude planned engineering)
        unplanned = []
        planned = []
        for inc in incidents:
            planned_el = inc.find("inc:Planned", NS)
            is_planned = planned_el is not None and planned_el.text.strip().lower() == "true"
            summary_el = inc.find("inc:Summary", NS)
            desc_el = inc.find("inc:Description", NS)
            summary = summary_el.text.strip() if summary_el is not None and summary_el.text else ""
            description = _strip_html(desc_el.text) if desc_el is not None and desc_el.text else ""

            # Get affected operators
            operators = []
            for op in inc.findall(".//inc:Affects/inc:Operators/inc:AffectedOperator/inc:OperatorName", NS):
                if op.text:
                    operators.append(op.text.strip())

            entry = {
                "summary": summary,
                "description": description[:300] + "..." if len(description) > 300 else description,
                "operators": operators,
                "planned": is_planned,
            }

            if is_planned:
                planned.append(entry)
            else:
                unplanned.append(entry)

        lines = []

        if unplanned:
            lines.append("<b>⚠ Active Disruptions:</b><br>")
            for i, d in enumerate(unplanned[:3], 1):
                lines.append(f"<b>{i}. {d['summary']}</b>")
                if d["operators"]:
                    lines.append(f"Affects: {', '.join(d['operators'])}")
                if d["description"]:
                    lines.append(d["description"])
                lines.append("")
        else:
            lines.append("No unplanned disruptions currently reported.<br>")

        if planned:
            lines.append("<b>🔧 Planned Engineering Work:</b><br>")
            for i, d in enumerate(planned[:3], 1):
                lines.append(f"<b>{i}. {d['summary']}</b>")
                if d["operators"]:
                    lines.append(f"Affects: {', '.join(d['operators'])}")
                lines.append("")

        lines.append(
            f"<a href='{FALLBACK_URL}' target='_blank'>View all disruptions on National Rail →</a>"
        )

        return {
            "status": "ok",
            "message": "<br>".join(lines)
        }

    except requests.Timeout:
        return _fallback("The disruptions feed timed out.")
    except requests.ConnectionError:
        return _fallback("Could not connect to National Rail.")
    except ET.ParseError:
        return _fallback("Could not parse the disruptions feed.")
    except Exception as e:
        return _fallback(f"An error occurred: {e}")


def _fallback(reason: str = "") -> dict:
    msg = "I was unable to fetch the latest disruption information."
    if reason:
        msg += f" ({reason})"
    return {
        "status": "error",
        "message": (
            f"{msg}<br><br>"
            f"Please check the National Rail website for live disruption information:<br>"
            f"<a href='{FALLBACK_URL}' target='_blank'>National Rail Status and Disruptions →</a>"
        )
    }