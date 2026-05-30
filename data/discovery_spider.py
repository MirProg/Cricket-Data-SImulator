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
    
    # We will seed the queue with a massive block of 100,000 IDs for the multithreaded load balancer
    base_id = 1410000 # Seed block
    new_matches = 0
    
    for i in range(100000):
        ca_match_id = str(base_id + i)
        
        try:
            conn.execute('INSERT INTO CrawlQueue (ca_match_id, status) VALUES (?, ?)', (ca_match_id, 'PENDING'))
            new_matches += 1
        except sqlite3.IntegrityError:
            pass
            
    conn.commit()
    conn.close()
    logger.info(f"Discovery complete. Added {new_matches} new matches to the CrawlQueue.")

if __name__ == "__main__":
    run_discovery()
