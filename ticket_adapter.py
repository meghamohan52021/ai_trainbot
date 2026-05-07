import requests
import xml.etree.ElementTree as ET
from datetime import datetime

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
        csv_path = os.path.join(os.path.dirname(__file__), "StationNameAndCode.csv")
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
        t = time_pref["time"] if time_pref and "time" in time_pref else "09:00"
        return f"{date_str}T{t}:00"

    def _build_request(self, journey: dict) -> str:
        from_crs = self._crs(journey.get("from_station", ""))
        to_crs   = self._crs(journey.get("to_station", ""))
        dt       = self._dt(journey.get("depart_date"), journey.get("depart_time_pref"))
        pref     = journey.get("depart_time_pref")

        tag = "departBy"
        if pref:
            if pref.get("type") == "after":
                tag = "departAfter"
            elif pref.get("type") == "before":
                tag = "arriveBefore"

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

        best_pence = None
        best_j = None

        for j in journeys:
            for fare_el in j.findall(f".//{{{NS_COM}}}totalPrice"):
                try:
                    p = int(fare_el.text)
                except (ValueError, TypeError):
                    continue
                if best_pence is None or p < best_pence:
                    best_pence = p
                    best_j = j

        if best_j is None:
            return self._no_fare(journeys[0], journey)

        sched = best_j.find(f".//{{{NS_JPS}}}timetable/{{{NS_JPS}}}scheduled")
        dep = arr = ""
        if sched is not None:
            d = sched.findtext(f"{{{NS_JPS}}}departure")
            a = sched.findtext(f"{{{NS_JPS}}}arrival")
            if d:
                dep = d[11:16]
            if a:
                arr = a[11:16]

        op_el = best_j.find(f".//{{{NS_JPS}}}operator/{{{NS_COM}}}name")
        operator = op_el.text if op_el is not None else "National Rail"

        price = f"£{best_pence / 100:.2f}"
        from_crs = self._crs(journey.get("from_station", ""))
        to_crs   = self._crs(journey.get("to_station", ""))
        date     = journey.get("depart_date", "").replace("-", "")
        link = (
            f"https://www.nationalrail.co.uk/journey-planner/"
            f"?type=single&origin={from_crs}&destination={to_crs}"
            f"&leavingDate={date}&leavingHour={dep[:2]}&leavingMin={dep[3:]}"
        )

        return {
            "status": "success",
            "price": price,
            "provider": operator,
            "departure_time": dep,
            "arrival_time": arr,
            "booking_link": link,
            "message": (
                f"Cheapest ticket: {price}\n"
                f"Operator: {operator}\n"
                f"Departs: {dep} → Arrives: {arr}\n\n"
                f"Book here: {link}"
            )
        }

    def _no_fare(self, journey, jdict: dict) -> dict:
        sched = journey.find(f".//{{{NS_JPS}}}timetable/{{{NS_JPS}}}scheduled")
        dep = arr = ""
        if sched is not None:
            d = sched.findtext(f"{{{NS_JPS}}}departure")
            a = sched.findtext(f"{{{NS_JPS}}}arrival")
            if d: dep = d[11:16]
            if a: arr = a[11:16]

        from_crs = self._crs(jdict.get("from_station", ""))
        to_crs   = self._crs(jdict.get("to_station", ""))
        date     = jdict.get("depart_date", "").replace("-", "")
        link = (
            f"https://www.nationalrail.co.uk/journey-planner/"
            f"?type=single&origin={from_crs}&destination={to_crs}&leavingDate={date}"
        )
        return {
            "status": "success",
            "price": "See booking link",
            "provider": "National Rail",
            "departure_time": dep,
            "arrival_time": arr,
            "booking_link": link,
            "message": f"Journey found: departs {dep}, arrives {arr}.\nFare details unavailable - book directly:\n{link}"
        }

    def _err(self, msg: str) -> dict:
        return {
            "status": "error",
            "price": None,
            "provider": None,
            "departure_time": None,
            "arrival_time": None,
            "booking_link": "https://www.nationalrail.co.uk",
            "message": f"{msg}\n\nSearch manually at: https://www.nationalrail.co.uk"
        }

    def search_cheapest(self, journey: dict) -> dict:
        from_crs = self._crs(journey.get("from_station", ""))
        to_crs   = self._crs(journey.get("to_station", ""))

        if not from_crs:
            return self._err(f"Could not find CRS code for '{journey.get('from_station')}'.")
        if not to_crs:
            return self._err(f"Could not find CRS code for '{journey.get('to_station')}'.")

        try:
            resp = requests.post(
                RTJP_ENDPOINT,
                data=self._build_request(journey).encode("utf-8"),
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
