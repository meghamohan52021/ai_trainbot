import requests

token = "rishitathummala223@gmail.com:1779983580000:-P16QSE1qDJVdoZ6dNxghHEI3r6VkS7UvDATiKlM978="

resp = requests.get(
    "https://opendata.nationalrail.co.uk/api/staticfeeds/5.0/incidents",
    headers={"X-Auth-Token": token},
    timeout=10
)
print("Status:", resp.status_code)
print("Response:", resp.text[:2000])