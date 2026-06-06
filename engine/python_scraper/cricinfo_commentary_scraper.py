import sqlite3
import os
import time
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from curl_cffi import requests

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "commentary_archive.sqlite"))
MAX_WORKERS = 50

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS Commentary (
            match_id TEXT PRIMARY KEY,
            title TEXT,
            raw_json TEXT
        )
    ''')
    conn.commit()
    conn.close()

def fetch_commentary(match_id):
    try:
        # Step 1: Hit the generic match endpoint to get the redirect/slugs
        url = f"https://www.espncricinfo.com/matches/engine/match/{match_id}.html"
        r1 = requests.get(url, impersonate="chrome110", timeout=15)
        
        if r1.status_code == 404:
            return match_id, None, None, "404"
            
        m1 = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', r1.text)
        if not m1:
            return match_id, None, None, "No Data Block"
            
        data1 = json.loads(m1.group(1))
        
        # Check if it's actually a match page
        if 'match' not in data1['props']['appPageProps']['data']:
            return match_id, None, None, "Not a Match"
            
        match_data = data1['props']['appPageProps']['data']['match']
        match_slug = match_data.get('slug')
        series_slug = match_data.get('series', {}).get('slug')
        title = match_data.get('title')
        
        if not match_slug or not series_slug:
            return match_id, title, None, "Missing Slugs"
            
        # Step 2: Fetch the ball-by-ball commentary page
        comm_url = f"https://www.espncricinfo.com/series/{series_slug}/match/{match_slug}-{match_id}/ball-by-ball-commentary"
        r2 = requests.get(comm_url, impersonate="chrome110", timeout=15)
        
        if r2.status_code == 404:
            return match_id, title, None, "No Commentary Page"
            
        m2 = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', r2.text)
        if not m2:
            return match_id, title, None, "No Commentary Data Block"
            
        data2 = json.loads(m2.group(1))
        
        return match_id, title, json.dumps(data2), "200"
        
    except Exception as e:
        return match_id, None, None, str(e)

def main():
    print("Initializing ESPNCricinfo Commentary Scraper...")
    init_db()
    
    # Example starting ID for modern era T20/ODIs where commentary exists
    start_id = 1410400 
    batch_size = 50
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print(f"Starting iteration from match ID: {start_id}")
    current_id = start_id
    
    while True:
        batch_ids = list(range(current_id, current_id + batch_size))
        print(f"Processing batch {batch_ids[0]} - {batch_ids[-1]}...")
        
        results = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(fetch_commentary, m_id): m_id for m_id in batch_ids}
            for future in as_completed(futures):
                m_id, title, raw_json, status = future.result()
                
                if status == "200" and raw_json:
                    results.append((str(m_id), title, raw_json))
                    print(f"Match {m_id}: Downloaded Commentary ({title})")
                elif status not in ["404", "Not a Match", "No Data Block"]:
                    print(f"Match {m_id}: Status -> {status}")
                    
        if results:
            cursor.executemany("INSERT OR REPLACE INTO Commentary (match_id, title, raw_json) VALUES (?, ?, ?)", results)
            conn.commit()
            print(f">>> Inserted {len(results)} commentaries into DB.")
            
        current_id += batch_size

if __name__ == "__main__":
    main()
