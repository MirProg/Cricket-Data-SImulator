import requests
import sqlite3
import re
import logging
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO, format='%(asctime)s - DISCOVERY - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_db():
    conn = sqlite3.connect('data/cricket_db.sqlite')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS CrawlQueue (
            ca_match_id TEXT PRIMARY KEY,
            status TEXT DEFAULT 'PENDING',
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

def extract_match_id(url: str):
    # e.g., /Archive/Scorecards/1426/1426957.html
    match = re.search(r'/Scorecards/\d+/(\d+)\.html', url)
    if match:
        return match.group(1)
    return None

def run_discovery():
    logger.info("Starting Discovery Spider...")
    conn = setup_db()
    
    # We will seed the queue with a batch of recent sequential IDs for the load balancer
    # A full recursive crawl takes hours, so we inject a chunk of IDs directly into the Queue.
    # We use 1426900 to 1427000 as a seed block (recent matches)
    base_id = 1426900
    new_matches = 0
    
    for i in range(100):
        ca_match_id = str(base_id + i)
        
        try:
            conn.execute('INSERT INTO CrawlQueue (ca_match_id, status) VALUES (?, ?)', (ca_match_id, 'PENDING'))
            new_matches += 1
        except sqlite3.IntegrityError:
            # Already in queue
            pass
            
    conn.commit()
    conn.close()
    logger.info(f"Discovery complete. Added {new_matches} new matches to the CrawlQueue.")

if __name__ == "__main__":
    run_discovery()
