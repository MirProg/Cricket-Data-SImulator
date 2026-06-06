import sqlite3
import os
import time
from curl_cffi import requests
from bs4 import BeautifulSoup
import browser_cookie3

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "master_archive.sqlite"))
MAX_CONSECUTIVE_404 = 5

def get_cookies():
    try:
        cj = browser_cookie3.firefox(domain_name='cricketarchive.com')
        return {c.name: c.value for c in cj}
    except Exception as e:
        print(f"Cookie Error: {e}")
        return {}

def get_max_id():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT MAX(match_id) FROM ScrapedMatches")
    max_id = c.fetchone()[0]
    conn.close()
    return max_id if max_id else 0

def fetch_match(match_id, cookies):
    url = f"https://cricketarchive.com/Archive/Scorecards/{match_id // 1000}/{match_id}.html"
    try:
        response = requests.get(url, impersonate="chrome110", cookies=cookies, timeout=15)
        if response.status_code == 404:
            return None, "404"
        if response.status_code == 200:
            if "Access Denied" in response.text:
                return None, "Access Denied"
            soup = BeautifulSoup(response.text, "lxml")
            tables = soup.find_all("table")
            if not tables:
                return None, "No Data Block"
                
            title, venue = "", ""
            for row in tables[0].find_all("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    val = cells[1].get_text(strip=True)
                    if "venue" in label:
                        venue = val
                    elif not title:
                        title = val
            return (title, venue), "200"
        return None, str(response.status_code)
    except Exception as e:
        return None, str(e)

def main():
    print("Starting Daily Match Updater for CricketArchive...")
    cookies = get_cookies()
    start_id = get_max_id() + 1
    print(f"Checking for new matches starting at ID: {start_id}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    consecutive_404 = 0
    current_id = start_id
    new_matches = []
    
    while consecutive_404 < MAX_CONSECUTIVE_404:
        data, status = fetch_match(current_id, cookies)
        if status == "404":
            consecutive_404 += 1
            print(f"Match {current_id}: 404 Not Found ({consecutive_404}/{MAX_CONSECUTIVE_404})")
        elif status == "200" and data:
            title, venue = data
            if title or venue:
                new_matches.append((current_id, title, venue))
                print(f"Match {current_id}: Added ({title})")
            consecutive_404 = 0
        else:
            print(f"Match {current_id}: Unusual Status -> {status}")
            consecutive_404 = 0
            
        current_id += 1
        time.sleep(1) # Polite delay
        
    if new_matches:
        cursor.executemany("INSERT OR REPLACE INTO ScrapedMatches (match_id, title, venue, series, date_text, format, toss, result, balls_per_over) VALUES (?, ?, ?, '', '', '', '', '', '')", new_matches)
        conn.commit()
        print(f"Successfully added {len(new_matches)} new matches to the database!")
    else:
        print("No new matches found today.")
        
    conn.close()

if __name__ == "__main__":
    main()
