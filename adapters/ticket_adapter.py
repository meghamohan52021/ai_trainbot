import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

RTJP_USERNAME = "wwang"
RTJP_PASSWORD = "?i92S6"
RTJP_ENDPOINT = "https://ojp.nationalrail.co.uk/webservices/jpdlr"

NS_SOAP = "http://schemas.xmlsoap.org/soap/envelope/"
NS_JPS  = "http://www.thalesgroup.com/ojp/jpdlr"
NS_COM  = "http://www.thalesgroup.com/ojp/common"


class TicketSearchAdapter:

    def _crs(self, station_name: str) -> str:
        if not station_name:
            return ""
        import csv, os
        csv_path =  Path(__file__).resolve().parent.parent / "StationNameAndCode.csv"
        try:
            with open(csv_path, newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))[1:]
            for row in rows:
                if len(row) >= 2 and row[0].strip().lower() == station_name.lower():
                    return row[1].strip()
            for row in rows:
                if len(row) >= 2 and station_name.lower() in row[0].strip().lower():
                    return row[1].strip()
        except FileNotFoundError:
            pass
        return ""

    def _dt(self, date_str: str, time_pref: dict) -> str:
        if not date_str:
            return datetime.now().strftime("%Y-%m-%dT09:00:00")

        if time_pref and isinstance(time_pref, dict):
            t_type = time_pref.get("type")
            if t_type in {"before", "after", "at"} and "time" in time_pref:
                t = time_pref["time"]
            elif t_type == "between" and "start" in time_pref:
                t = time_pref["start"]
            else:
                t = "09:00"
        else:
            t = "09:00"

        return f"{date_str}T{t}:00"

    def _format_date(self, date_str: str) -> str:
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.strftime("%d%m%y")
        except (ValueError, TypeError):
            return ""

    def _round_min(self, dep: str, round_up: bool = False) -> tuple:
        if not dep:
            return "09", "00"
        hour = dep[:2]
        try:
            raw_min = int(dep[3:]) if len(dep) > 3 else 0
        except ValueError:
            raw_min = 0

        if round_up:
            rounded = ((raw_min + 14) // 15) * 15
        else:
            rounded = (raw_min // 15) * 15

        if rounded >= 60:
            try:
                hour = str(int(hour) + 1).zfill(2)
            except ValueError:
                pass
            rounded = 0

        return hour, str(rounded).zfill(2)

    def _build_link(self, from_crs: str, to_crs: str, journey: dict, dep: str) -> str:
        journey_type = (journey.get("journey_type") or "single").lower()
        pref = journey.get("depart_time_pref")
        round_up = pref and isinstance(pref, dict) and pref.get("type") == "before"

        leaving_date = self._format_date(journey.get("depart_date", "") or "")
        leaving_hour, leaving_min = self._round_min(dep, round_up=round_up)

        if journey_type == "return" and journey.get("return_date") == "open":
            return (
                f"https://www.nationalrail.co.uk/journey-planner/"
                f"?type=open&origin={from_crs}&destination={to_crs}"
                f"&leavingType=departing&leavingDate={leaving_date}"
                f"&leavingHour={leaving_hour}&leavingMin={leaving_min}"
                f"&adults=1&extraTime=0#O"
            )

        if journey_type == "return":
            return_date = self._format_date(journey.get("return_date", "") or "")
            return_pref = journey.get("return_time_pref")
            if return_pref and isinstance(return_pref, dict) and "time" in return_pref:
                return_time = return_pref["time"]
                return_round_up = return_pref.get("type") == "before"
            else:
                return_time = "09:00"
                return_round_up = False
            return_hour, return_min = self._round_min(return_time, round_up=return_round_up)

            return (
                f"https://www.nationalrail.co.uk/journey-planner/"
                f"?type=return&origin={from_crs}&destination={to_crs}"
                f"&leavingType=departing&leavingDate={leaving_date}"
                f"&leavingHour={leaving_hour}&leavingMin={leaving_min}"
                f"&returnType=departing&returnDate={return_date}"
                f"&returnHour={return_hour}&returnMin={return_min}"
                f"&adults=1&extraTime=0#O"
            )

        else:
            return (
                f"https://www.nationalrail.co.uk/journey-planner/"
                f"?type=single&origin={from_crs}&destination={to_crs}"
                f"&leavingType=departing&leavingDate={leaving_date}"
                f"&leavingHour={leaving_hour}&leavingMin={leaving_min}"
                f"&adults=1&extraTime=0#O"
            )

    def _build_request(self, journey: dict) -> str:
        from_crs = self._crs(journey.get("from_station", ""))
        to_crs   = self._crs(journey.get("to_station", ""))
        dt       = self._dt(journey.get("depart_date"), journey.get("depart_time_pref"))
        pref     = journey.get("depart_time_pref")

        tag = "departBy"
        if pref and isinstance(pref, dict):
            if pref.get("type") == "before":
                tag = "arriveBy"

        return f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:jpd="http://www.thalesgroup.com/ojp/jpdlr"
    xmlns:com="http://www.thalesgroup.com/ojp/common">
  <soapenv:Header/>
  <soapenv:Body>
    <jpd:RealtimeJourneyPlanRequest>
      <jpd:origin><com:stationCRS>{from_crs}</com:stationCRS></jpd:origin>
      <jpd:destination><com:stationCRS>{to_crs}</com:stationCRS></jpd:destination>
      <jpd:realtimeEnquiry>STANDARD</jpd:realtimeEnquiry>
      <jpd:outwardTime><jpd:{tag}>{dt}</jpd:{tag}></jpd:outwardTime>
      <jpd:directTrains>false</jpd:directTrains>
      <jpd:fareRequestDetails>
        <jpd:passengers><com:adult>1</com:adult><com:child>0</com:child></jpd:passengers>
        <jpd:fareClass>ANY</jpd:fareClass>
      </jpd:fareRequestDetails>
      <jpd:includeAdditionalInformation>true</jpd:includeAdditionalInformation>
    </jpd:RealtimeJourneyPlanRequest>
  </soapenv:Body>
</soapenv:Envelope>"""

    def _parse(self, xml_text: str, journey: dict) -> dict:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            return self._err(f"Failed to parse API response: {e}")

        body = root.find(f".//{{{NS_SOAP}}}Body")
        if body is None:
            return self._err("Empty response from API.")

        fault = body.find(f".//{{{NS_JPS}}}RealtimeJourneyPlanFault")
        if fault is not None:
            code = fault.findtext(f"{{{NS_COM}}}response") or "Unknown"
            detail = fault.findtext(f"{{{NS_COM}}}responseDetails") or ""
            return self._err(f"API error: {code}. {detail}")

        journeys = body.findall(f".//{{{NS_JPS}}}outwardJourney")
        if not journeys:
            return self._err("No journeys found for this route and date.")

        journey_type = (journey.get("journey_type") or "single").lower()
        preferred_direction = "RETURN" if journey_type == "return" else "OUTWARD"

        best_pence = None
        best_j = None
        best_fare_desc = None

        for j in journeys:
            fares = j.findall(f"{{{NS_JPS}}}fare")
            matched_fares = [
                f for f in fares
                if (f.findtext(f"{{{NS_COM}}}direction") or "").upper() == preferred_direction
            ]
            if not matched_fares:
                matched_fares = fares

            for fare in matched_fares:
                try:
                    p = int(fare.findtext(f"{{{NS_COM}}}totalPrice") or "")
                except (ValueError, TypeError):
                    continue
                desc = fare.findtext(f"{{{NS_COM}}}description") or ""
                if best_pence is None or p < best_pence:
                    best_pence = p
                    best_j = j
                    best_fare_desc = desc

        if best_j is None:
            return self._no_fare(journeys[0], journey)

        sched = best_j.find(f"{{{NS_JPS}}}timetable/{{{NS_JPS}}}scheduled")
        dep = arr = ""
        if sched is not None:
            d = sched.findtext(f"{{{NS_JPS}}}departure")
            a = sched.findtext(f"{{{NS_JPS}}}arrival")
            if d:
                dep = d[11:16]
            if a:
                arr = a[11:16]

        op_el = best_j.find(f".//{{{NS_COM}}}name")
        operator = op_el.text if op_el is not None else "National Rail"

        price    = f"£{best_pence / 100:.2f}"
        from_crs = self._crs(journey.get("from_station", ""))
        to_crs   = self._crs(journey.get("to_station", ""))
        link     = self._build_link(from_crs, to_crs, journey, dep)

        return {
            "status": "success",
            "price": price,
            "provider": operator,
            "departure_time": dep,
            "arrival_time": arr,
            "booking_link": link,
            "message": (
                f"Cheapest ticket: <b>{price}</b> ({best_fare_desc})<br>"
                f"Operator: {operator}<br>"
                f"Departs: {dep} → Arrives: {arr}<br><br>"
                f"<a href='{link}' target='_blank'>Book on National Rail →</a>"
            )
        }

    def _no_fare(self, journey, jdict: dict) -> dict:
        sched = journey.find(f"{{{NS_JPS}}}timetable/{{{NS_JPS}}}scheduled")
        dep = arr = ""
        if sched is not None:
            d = sched.findtext(f"{{{NS_JPS}}}departure")
            a = sched.findtext(f"{{{NS_JPS}}}arrival")
            if d:
                dep = d[11:16]
            if a:
                arr = a[11:16]

        from_crs = self._crs(jdict.get("from_station", ""))
        to_crs   = self._crs(jdict.get("to_station", ""))
        link     = self._build_link(from_crs, to_crs, jdict, dep)

        return {
            "status": "success",
            "price": "See booking link",
            "provider": "National Rail",
            "departure_time": dep,
            "arrival_time": arr,
            "booking_link": link,
            "message": (
                f"Journey found: departs {dep}, arrives {arr}.<br>"
                f"Fare details unavailable - book directly:<br>"
                f"<a href='{link}' target='_blank'>Book on National Rail →</a>"
            )
        }

    def _err(self, msg: str) -> dict:
        return {
            "status": "error",
            "price": None,
            "provider": None,
            "departure_time": None,
            "arrival_time": None,
            "booking_link": "https://www.nationalrail.co.uk",
            "message": (
                f"{msg}<br><br>"
                f"<a href='https://www.nationalrail.co.uk' target='_blank'>Search on National Rail →</a>"
            )
        }

    def search_cheapest(self, journey: dict) -> dict:
        from_crs = self._crs(journey.get("from_station", ""))
        to_crs   = self._crs(journey.get("to_station", ""))

        if not from_crs:
            return self._err(f"Could not find CRS code for '{journey.get('from_station')}'.")
        if not to_crs:
            return self._err(f"Could not find CRS code for '{journey.get('to_station')}'.")

        xml_body = self._build_request(journey)

        try:
            resp = requests.post(
                RTJP_ENDPOINT,
                data=xml_body.encode("utf-8"),
                headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": ""},
                auth=(RTJP_USERNAME, RTJP_PASSWORD),
                timeout=15,
            )
        except requests.Timeout:
            return self._err("The National Rail API timed out.")
        except requests.ConnectionError:
            return self._err("Could not connect to the National Rail API.")

        if resp.status_code != 200:
            return self._err(f"API returned status {resp.status_code}.")

        return self._parse(resp.text, journey)