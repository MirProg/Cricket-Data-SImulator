import os
import json
import sqlite3
import time
import logging
from scrapling import Fetcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - CRICBUZZ_DEEP_SCRAPER - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

JSONL_PATH = "D:/cricket_data/cricbuzz_history_db.jsonl"
DB_PATH = "D:/cricket_data/cricmatrix.db"

def init_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cricbuzz_raw_html (
            match_id TEXT PRIMARY KEY,
            html TEXT
        )
    """)

def run_deep_scraper():
    logger.info("[*] Starting Stealth Cricbuzz Deep Scraper using Scrapling...")
    
    # Connect to DB
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    
    # Load targets
    matches_to_scrape = []
    if os.path.exists(JSONL_PATH):
        with open(JSONL_PATH, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    matches_to_scrape.append(data)
                except json.JSONDecodeError:
                    continue
                
    logger.info(f"[*] Loaded {len(matches_to_scrape)} matches from metadata file.")
    
    # Initialize Scrapling Fetcher (undetectable)
    fetcher = Fetcher()
    
    # Run the full infinite loop
    for match in matches_to_scrape:
        match_id = match['match_id']
        url = match['url']
        
        # Check if already scraped
        cursor = conn.execute("SELECT 1 FROM cricbuzz_raw_html WHERE match_id = ?", (match_id,))
        if cursor.fetchone():
            continue
            
        logger.info(f"[*] Deep scraping match {match_id}: {url}")
        try:
            import requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8'
            }
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                html_content = response.text
                
                # Save raw HTML into DB for later ETL
                conn.execute("INSERT OR IGNORE INTO cricbuzz_raw_html (match_id, html) VALUES (?, ?)", (match_id, html_content))
                conn.commit()
                
                logger.info(f"[+] Successfully saved raw HTML for {match_id}")
            else:
                logger.error(f"[!] HTTP Error {response.status_code} for {match_id}")
            time.sleep(2) # Polite delay
        except Exception as e:
            logger.error(f"[!] Fetch failed for {match_id}: {e}")
            
    conn.close()
    logger.info("[+] Deep Scraper Run Complete.")

if __name__ == "__main__":
    run_deep_scraper()
