
import requests
import xml.etree.ElementTree as ET

RTJP_USERNAME = "wwang"
RTJP_PASSWORD = "?i92S6"
RTJP_ENDPOINT = "https://ojp.nationalrail.co.uk/webservices/jpdlr"

SOAP_REQUEST = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:jpd="http://www.thalesgroup.com/ojp/jpdlr"
    xmlns:com="http://www.thalesgroup.com/ojp/common">
  <soapenv:Header/>
  <soapenv:Body>
    <jpd:RealtimeJourneyPlanRequest>
      <jpd:origin><com:stationCRS>NRW</com:stationCRS></jpd:origin>
      <jpd:destination><com:stationCRS>OXF</com:stationCRS></jpd:destination>
      <jpd:realtimeEnquiry>STANDARD</jpd:realtimeEnquiry>
      <jpd:outwardTime>
        <jpd:departBy>2026-07-20T09:00:00</jpd:departBy>
      </jpd:outwardTime>
      <jpd:directTrains>false</jpd:directTrains>
      <jpd:fareRequestDetails>
        <jpd:passengers>
          <com:adult>1</com:adult>
          <com:child>0</com:child>
        </jpd:passengers>
        <jpd:fareClass>ANY</jpd:fareClass>
      </jpd:fareRequestDetails>
    </jpd:RealtimeJourneyPlanRequest>
  </soapenv:Body>
</soapenv:Envelope>"""

print("Testing National Rail RTJP API")
print(f"Endpoint: {RTJP_ENDPOINT}")
print("Route: Norwich (NRW) → Oxford (OXF), 2026-07-20\n")

response = requests.post(
    RTJP_ENDPOINT,
    data=SOAP_REQUEST.encode("utf-8"),
    headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": ""},
    auth=(RTJP_USERNAME, RTJP_PASSWORD),
    timeout=15,
)

print(f"Status: {response.status_code}\n")

if response.status_code == 200:
    # Parse and print a clean summary
    root = ET.fromstring(response.text)
    ns_jps = "http://www.thalesgroup.com/ojp/jpdlr"
    ns_com = "http://www.thalesgroup.com/ojp/common"

    journeys = root.findall(f".//{{{ns_jps}}}outwardJourney")
    print(f"Journeys found: {len(journeys)}\n")

    for j in journeys[:3]:  # Show first 3
        jid = j.findtext(f"{{{ns_jps}}}id")
        scheduled = j.find(f".//{{{ns_jps}}}timetable/{{{ns_jps}}}scheduled")
        dep = scheduled.findtext(f"{{{ns_jps}}}departure")[11:16] if scheduled is not None else "?"
        arr = scheduled.findtext(f"{{{ns_jps}}}arrival")[11:16] if scheduled is not None else "?"

        # Get fares
        fares = j.findall(f".//{{{ns_com}}}totalPrice")
        prices = [int(f.text) for f in fares if f.text]

        print(f"Journey {jid}: {dep} → {arr}")
        if prices:
            cheapest = min(prices)
            print(f"  Cheapest fare: £{cheapest/100:.2f}")
        else:
            print(f"  No fares returned")

        # Operators
        ops = j.findall(f".//{{{ns_com}}}name")
        op_names = list(set(o.text for o in ops if o.text))
        if op_names:
            print(f"  Operators: {', '.join(op_names)}")
        print()
else:
    print(f"Error response:\n{response.text[:500]}")