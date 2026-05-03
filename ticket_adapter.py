import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# ── API credentials ────────────────────────────────────────────────────────────
RTJP_USERNAME = "wwang"
RTJP_PASSWORD = "?i92S6"
RTJP_ENDPOINT = "https://ojp.nationalrail.co.uk/webservices/jpdlr"

NS_SOAP = "http://schemas.xmlsoap.org/soap/envelope/"
NS_JPS  = "http://www.thalesgroup.com/ojp/jpdlr"
NS_COM  = "http://www.thalesgroup.com/ojp/common"


class TicketSearchAdapter:
    """
    Connects to the National Rail RTJP SOAP API to find the cheapest
    available train ticket for a given journey.
    """

    def _get_crs(self, station_name: str) -> str:
        """
        Converts a station name to its 3-letter CRS code using
        StationNameAndCode.csv — the same source used by station_data.py.
        This ensures a single source of truth for station data.
        """
        if not station_name:
            return ""
        import csv, os
        csv_path = os.path.join(os.path.dirname(__file__), "StationNameAndCode.csv")
        try:
            with open(csv_path, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader)  # skip header
                rows = list(reader)

            # Pass 1: exact match on station name
            for row in rows:
                if len(row) < 2:
                    continue
                if row[0].strip().lower() == station_name.lower():
                    return row[1].strip()

            # Pass 2: partial match (e.g. "Waterloo" matches "London Waterloo")
            for row in rows:
                if len(row) < 2:
                    continue
                if station_name.lower() in row[0].strip().lower():
                    return row[1].strip()

        except FileNotFoundError:
            pass

        return ""

    def _build_datetime(self, date_str: str, time_pref: dict) -> str:
        """
        Builds ISO datetime string for the API.
        If a time preference exists, use it. Otherwise default to 09:00.
        """
        if not date_str:
            return datetime.now().strftime("%Y-%m-%dT09:00:00")

        time_str = "09:00"
        if time_pref and "time" in time_pref:
            time_str = time_pref["time"]

        return f"{date_str}T{time_str}:00"

    def _build_soap_request(self, journey_dict: dict) -> str:
        """
        Builds the SOAP XML request body for RealtimeJourneyPlanRequest.
        Includes fareRequestDetails to get fare information back.
        """
        from_crs = self._get_crs(journey_dict.get("from_station", ""))
        to_crs   = self._get_crs(journey_dict.get("to_station", ""))

        depart_dt = self._build_datetime(
            journey_dict.get("depart_date"),
            journey_dict.get("depart_time_pref")
        )

        time_pref = journey_dict.get("depart_time_pref")
        time_tag = "departBy"
        if time_pref and time_pref.get("type") == "after":
            time_tag = "departAfter"
        elif time_pref and time_pref.get("type") == "before":
            time_tag = "arriveBefore"

        soap = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:jpd="http://www.thalesgroup.com/ojp/jpdlr"
    xmlns:com="http://www.thalesgroup.com/ojp/common">
  <soapenv:Header/>
  <soapenv:Body>
    <jpd:RealtimeJourneyPlanRequest>
      <jpd:origin>
        <com:stationCRS>{from_crs}</com:stationCRS>
      </jpd:origin>
      <jpd:destination>
        <com:stationCRS>{to_crs}</com:stationCRS>
      </jpd:destination>
      <jpd:realtimeEnquiry>STANDARD</jpd:realtimeEnquiry>
      <jpd:outwardTime>
        <jpd:{time_tag}>{depart_dt}</jpd:{time_tag}>
      </jpd:outwardTime>
      <jpd:directTrains>false</jpd:directTrains>
      <jpd:fareRequestDetails>
        <jpd:passengers>
          <com:adult>1</com:adult>
          <com:child>0</com:child>
        </jpd:passengers>
        <jpd:fareClass>ANY</jpd:fareClass>
      </jpd:fareRequestDetails>
      <jpd:includeAdditionalInformation>true</jpd:includeAdditionalInformation>
    </jpd:RealtimeJourneyPlanRequest>
  </soapenv:Body>
</soapenv:Envelope>"""
        return soap

    def _parse_response(self, xml_text: str, journey_dict: dict) -> dict:
        """
        Parses the SOAP XML response and extracts the cheapest fare
        and its corresponding journey details.
        """
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            return self._error(f"Failed to parse API response: {e}")

        # Check for fault
        body = root.find(f".//{{{NS_SOAP}}}Body")
        if body is None:
            return self._error("Empty response from API.")

        fault = body.find(f".//{{{NS_JPS}}}RealtimeJourneyPlanFault")
        if fault is not None:
            response_el = fault.find(f"{{{NS_COM}}}response")
            details_el  = fault.find(f"{{{NS_COM}}}responseDetails")
            code    = response_el.text if response_el is not None else "Unknown"
            details = details_el.text  if details_el  is not None else ""
            return self._error(f"API error: {code}. {details}")

        # Find all outward journeys
        journeys = body.findall(f".//{{{NS_JPS}}}outwardJourney")
        if not journeys:
            return self._error("No journeys found for this route and date.")

        best_price_pence = None
        best_journey     = None
        best_fare        = None

        for journey in journeys:
            fares = journey.findall(f".//{{{NS_COM}}}totalPrice")
            for fare_el in fares:
                try:
                    price_pence = int(fare_el.text)
                except (ValueError, TypeError):
                    continue
                if best_price_pence is None or price_pence < best_price_pence:
                    best_price_pence = price_pence
                    best_journey     = journey
                    # Find the fare element that has this price
                    for fare in journey.findall(f".//{{{NS_COM}}}id/../.."):
                        tp = fare.find(f"{{{NS_COM}}}totalPrice")
                        if tp is not None and tp.text == str(price_pence):
                            best_fare = fare
                            break

        if best_journey is None or best_price_pence is None:
            # Journeys found but no fares — return timetable only
            return self._timetable_only(journeys[0], journey_dict)

        # Extract departure and arrival times
        scheduled = best_journey.find(
            f".//{{{NS_JPS}}}timetable/{{{NS_JPS}}}scheduled"
        )
        dep_time = ""
        arr_time = ""
        if scheduled is not None:
            dep_el = scheduled.find(f"{{{NS_JPS}}}departure")
            arr_el = scheduled.find(f"{{{NS_JPS}}}arrival")
            if dep_el is not None and dep_el.text:
                dep_time = dep_el.text[11:16]  # Extract HH:MM from ISO string
            if arr_el is not None and arr_el.text:
                arr_time = arr_el.text[11:16]

        # Extract operator
        operator_el = best_journey.find(
            f".//{{{NS_JPS}}}operator/{{{NS_COM}}}name"
        )
        operator = operator_el.text if operator_el is not None else "National Rail"

        # Extract fare description
        desc_el = None
        if best_fare is not None:
            desc_el = best_fare.find(f"{{{NS_COM}}}description")
        fare_desc = desc_el.text if desc_el is not None else "Best available"

        # Convert pence to pounds
        price_str = f"£{best_price_pence / 100:.2f}"

        # Build National Rail booking link
        from_crs = self._get_crs(journey_dict.get("from_station", ""))
        to_crs   = self._get_crs(journey_dict.get("to_station", ""))
        date     = journey_dict.get("depart_date", "").replace("-", "")
        booking_link = (
            f"https://www.nationalrail.co.uk/journey-planner/"
            f"?type=single&origin={from_crs}&destination={to_crs}"
            f"&leavingDate={date}&leavingHour={dep_time[:2]}&leavingMin={dep_time[3:]}"
        )

        return {
            "status": "success",
            "price": price_str,
            "fare_type": fare_desc,
            "provider": operator,
            "departure_time": dep_time,
            "arrival_time": arr_time,
            "booking_link": booking_link,
            "message": (
                f"Cheapest ticket found: {fare_desc} at {price_str}\n"
                f"Operator: {operator}\n"
                f"Departs: {dep_time} → Arrives: {arr_time}\n\n"
                f"Book here: {booking_link}"
            )
        }

    def _timetable_only(self, journey, journey_dict: dict) -> dict:
        """
        Fallback when journeys are found but no fare data is returned.
        Returns timetable info with a link to book on National Rail.
        """
        scheduled = journey.find(
            f".//{{{NS_JPS}}}timetable/{{{NS_JPS}}}scheduled"
        )
        dep_time = ""
        arr_time = ""
        if scheduled is not None:
            dep_el = scheduled.find(f"{{{NS_JPS}}}departure")
            arr_el = scheduled.find(f"{{{NS_JPS}}}arrival")
            if dep_el is not None and dep_el.text:
                dep_time = dep_el.text[11:16]
            if arr_el is not None and arr_el.text:
                arr_time = arr_el.text[11:16]

        from_crs = self._get_crs(journey_dict.get("from_station", ""))
        to_crs   = self._get_crs(journey_dict.get("to_station", ""))
        date     = journey_dict.get("depart_date", "").replace("-", "")
        booking_link = (
            f"https://www.nationalrail.co.uk/journey-planner/"
            f"?type=single&origin={from_crs}&destination={to_crs}&leavingDate={date}"
        )

        return {
            "status": "success",
            "price": "See booking link",
            "fare_type": "Various",
            "provider": "National Rail",
            "departure_time": dep_time,
            "arrival_time": arr_time,
            "booking_link": booking_link,
            "message": (
                f"Journey found: departs {dep_time}, arrives {arr_time}.\n"
                f"Fare details not available — please book directly:\n{booking_link}"
            )
        }

    def _error(self, message: str) -> dict:
        return {
            "status": "error",
            "price": None,
            "fare_type": None,
            "provider": None,
            "departure_time": None,
            "arrival_time": None,
            "booking_link": "https://www.nationalrail.co.uk",
            "message": (
                f"{message}\n\n"
                "You can search manually at: https://www.nationalrail.co.uk"
            )
        }

    def search_cheapest(self, journey_dict: dict) -> dict:
        """
        Main entry point. Takes a journey dict from the chatbot state
        and returns the cheapest ticket found via the RTJP API.
        """
        from_station = journey_dict.get("from_station", "")
        to_station   = journey_dict.get("to_station", "")

        from_crs = self._get_crs(from_station)
        to_crs   = self._get_crs(to_station)

        if not from_crs:
            return self._error(
                f"Could not find CRS code for '{from_station}'. "
                "Please check the station name."
            )
        if not to_crs:
            return self._error(
                f"Could not find CRS code for '{to_station}'. "
                "Please check the station name."
            )

        soap_body = self._build_soap_request(journey_dict)

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "",
        }

        try:
            response = requests.post(
                RTJP_ENDPOINT,
                data=soap_body.encode("utf-8"),
                headers=headers,
                auth=(RTJP_USERNAME, RTJP_PASSWORD),
                timeout=15,
            )
        except requests.Timeout:
            return self._error(
                "The National Rail API timed out. Please try again."
            )
        except requests.ConnectionError:
            return self._error(
                "Could not connect to the National Rail API. "
                "Please check your internet connection."
            )

        if response.status_code != 200:
            return self._error(
                f"API returned status {response.status_code}. "
                "Please try again later."
            )

        return self._parse_response(response.text, journey_dict)