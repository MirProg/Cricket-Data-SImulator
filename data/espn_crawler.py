import os
import json
import time
import random
import logging
import threading
from bs4 import BeautifulSoup
from curl_cffi import requests
from curl_cffi.requests.exceptions import RequestException
from concurrent.futures import ThreadPoolExecutor, as_completed

# Logger setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - ESPN CRAWLER - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_PATH = 'data/espn_history_db.jsonl'
LOCK = threading.Lock()

def load_scraped_ids():
    scraped = set()
    if os.path.exists(DB_PATH):
        with open(DB_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    match_id = data.get('match_id')
                    if match_id:
                        scraped.add(str(match_id))
                except Exception:
                    pass
    return scraped

class ESPNCrawler:
    def __init__(self):
        pass

    def fetch_match(self, match_id: str, retries=3):
        url = f"https://www.espncricinfo.com/matches/engine/match/{match_id}.html"
        for attempt in range(retries):
            try:
                # Impersonate Chrome browser to bypass Akamai bot detection
                response = requests.get(url, impersonate='chrome120', timeout=15)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    title_tag = soup.find('title')
                    title = title_tag.text if title_tag else "Unknown Match"
                    
                    if "scorecard" in response.text.lower() or "scorecard" in response.url.lower():
                        match_data = {
                            "source": "espn",
                            "match_id": str(match_id),
                            "title": title.strip(),
                            "url": response.url,
                            "status": "Scraped",
                            "timestamp": time.time()
                        }
                        return True, match_data
                    return False, None
                elif response.status_code == 404:
                    return False, None
                
                # If status code is 403 or other errors, wait and retry
                time.sleep(random.uniform(1.0, 3.0))
            except RequestException as e:
                # Catch connection resets, timeouts, etc. and retry
                if attempt == retries - 1:
                    logger.debug(f"Failed to fetch {match_id} after {retries} attempts: {e}")
                    return False, None
                time.sleep(random.uniform(2.0, 5.0))
            except Exception:
                return False, None
        return False, None

def crawl_espn_range(start_id=1359400, end_id=1360000, max_threads=30):
    scraped_ids = load_scraped_ids()
    logger.info(f"Loaded {len(scraped_ids)} already scraped ESPN matches.")
    
    # Generate pending queue
    pending = [str(i) for i in range(start_id, end_id) if str(i) not in scraped_ids]
    logger.info(f"Prepared {len(pending)} pending ESPN IDs to crawl.")
    
    if not pending:
        logger.info("No pending ESPN IDs to crawl in this range.")
        return
        
    crawler = ESPNCrawler()
    success_count = 0
    
    # Use 30 threads for concurrent requests
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {executor.submit(crawler.fetch_match, mid): mid for mid in pending}
        
        for future in as_completed(futures):
            mid = futures[future]
            try:
                success, data = future.result()
                if success and data:
                    with LOCK:
                        with open(DB_PATH, 'a', encoding='utf-8') as f:
                            f.write(json.dumps(data, ensure_ascii=False) + '\n')
                    success_count += 1
                    if success_count % 10 == 0:
                        logger.info(f"Concurrently scraped {success_count} new ESPN matches...")
            except Exception:
                pass

    logger.info(f"ESPN crawl cycle complete. Successfully scraped {success_count} new matches.")

if __name__ == "__main__":
    # Start scanning from 1359400 to 1360000 with 30 curl_cffi threads
    crawl_espn_range(start_id=1359400, end_id=1360000, max_threads=30)
