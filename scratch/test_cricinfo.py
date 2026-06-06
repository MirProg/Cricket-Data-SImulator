import re
import json
from curl_cffi import requests

def fetch():
    print("Fetching ESPNCricinfo...")
    r = requests.get('https://www.espncricinfo.com/series/ipl-2024-1410320/kolkata-knight-riders-vs-sunrisers-hyderabad-final-1410452/ball-by-ball-commentary', impersonate='chrome110')
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', r.text)
    if m:
        data = json.loads(m.group(1))
        with open('cricinfo_test.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print("Saved to cricinfo_test.json")
    else:
        print("No NEXT_DATA block found")

fetch()
