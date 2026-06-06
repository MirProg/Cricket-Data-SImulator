import browser_cookie3
from curl_cffi import requests

cj = browser_cookie3.firefox(domain_name='cricketarchive.com')
cookies = {c.name: c.value for c in cj}
url = "https://cricketarchive.com/Archive/Scorecards/1455/1455541.html"
r = requests.get(url, impersonate="chrome110", cookies=cookies)
with open("ca_test.html", "w", encoding="utf-8") as f:
    f.write(r.text)
print("Saved to ca_test.html")
