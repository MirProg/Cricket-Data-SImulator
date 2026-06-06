import sqlite3
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from curl_cffi import requests
import browser_cookie3
from bs4 import BeautifulSoup

# Paths
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "master_archive.sqlite"))
MAX_WORKERS = 100 # Resetting to a safer limit for CricketArchive
MAX_MATCH_ID = 1500000

def get_cookies():
    print("Extracting Firefox cookies for CricketArchive...")
    cj = browser_cookie3.firefox(domain_name='cricketarchive.com')
    cookies = {}
    for c in cj:
        cookies[c.name] = c.value
    return cookies

def get_last_processed_id():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(match_id) FROM ScrapedMatches")
    result = cursor.fetchone()[0]
    conn.close()
    return result if result else 0

def fetch_match(match_id, cookies):
    url = f"https://cricketarchive.com/Archive/Scorecards/{match_id // 1000}/{match_id}.html"
    try:
        # TLS Spoofing to bypass Cloudflare
        response = requests.get(url, impersonate="chrome110", cookies=cookies, timeout=15)
        
        if response.status_code == 404:
            return match_id, None, None, "404"
            
        if response.status_code == 200:
            if "Access Denied" in response.text:
                return match_id, None, None, "Access Denied"
                
            # Parse HTML like the Rust script did
            soup = BeautifulSoup(response.text, "lxml")
            tables = soup.find_all("table")
            if not tables:
                return match_id, None, None, "No Data Block"
                
            meta_table = tables[0]
            title = ""
            venue = ""
            
            for row in meta_table.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    val = cells[1].get_text(strip=True)
                    if "venue" in label:
                        venue = val
                    elif not title:
                        title = val
            
            return match_id, title, venue, "200"
                
        return match_id, None, None, str(response.status_code)
    except Exception as e:
        return match_id, None, None, f"Error: {str(e)}"

def main():
    print("Initializing Python TLS-Spoofing Scraper for CricketArchive...")
    
    cookies = get_cookies()
    if not cookies:
        print("WARNING: No cookies found for cricketarchive.com! Requests might fail with Access Denied.")
        
    start_id = get_last_processed_id()
    print(f"Resuming from Match ID: {start_id}")
    
    current_batch_start = start_id + 1
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    total_scraped = 0
    start_time = time.time()

    while current_batch_start <= MAX_MATCH_ID:
        batch_end = min(current_batch_start + 1000, MAX_MATCH_ID + 1)
        batch_ids = list(range(current_batch_start, batch_end))
        
        print(f"\nDispatching Batch: {current_batch_start} to {batch_end-1} (Threads: {MAX_WORKERS})")
        
        results = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(fetch_match, m_id, cookies): m_id for m_id in batch_ids}
            
            for future in as_completed(futures):
                m_id, title, venue, status = future.result()
                if status == "200" and (title or venue):
                    results.append((m_id, title, venue))
                
                if status not in ["200", "404", "No Data Block"]:
                     print(f"Match {m_id}: Unusual Status -> {status}")
                     
        # Bulk Insert
        if results:
            cursor.executemany("INSERT OR REPLACE INTO ScrapedMatches (match_id, title, venue, series, date_text, format, toss, result, balls_per_over) VALUES (?, ?, ?, '', '', '', '', '', '')", results)
            conn.commit()
            
            total_scraped += len(results)
            elapsed = time.time() - start_time
            rate = (total_scraped / elapsed) * 3600 if elapsed > 0 else 0
            
            print(f">>> BATCH COMPLETE | Inserted: {len(results)} | Total: {total_scraped} | Est Speed: {rate:.0f} matches/hour")

        current_batch_start = batch_end

    conn.close()
    print("Scraping Complete.")

if __name__ == "__main__":
    main()
