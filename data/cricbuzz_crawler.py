import os
import json
import time
import random
import logging
import requests
import threading
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# Logger setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - CRICBUZZ CRAWLER - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_PATH = 'data/cricbuzz_history_db.jsonl'
LOCK = threading.Lock()

def load_scraped_ids():
    scraped = set()
    if os.path.exists(DB_PATH):
        with open(DB_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get('source') == 'cricbuzz':
                        match_id = data.get('match_id')
                        if match_id:
                            scraped.add(str(match_id))
                except Exception:
                    pass
    return scraped

class CricbuzzSpider:
    def __init__(self):
        self.headers = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        ]

    def fetch_match(self, match_id: str):
        url = f"https://www.cricbuzz.com/live-cricket-scorecard/{match_id}/"
        headers = {'User-Agent': random.choice(self.headers)}
        try:
            # Short timeout to avoid hanging threads
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                title_tag = soup.find('title')
                title = title_tag.text if title_tag else "Unknown Match"
                
                # Check if it is a real scorecard table or just a placeholder page
                if "scorecard" in response.text.lower() or soup.find('div', class_='cb-col cb-col-100 cb-ltst-wgt-hdr'):
                    match_data = {
                        "source": "cricbuzz",
                        "match_id": str(match_id),
                        "title": title.strip(),
                        "url": url,
                        "status": "Scraped",
                        "timestamp": time.time()
                    }
                    return True, match_data
                return False, None
            return False, None
        except Exception:
            return False, None

def crawl_cricbuzz_range(start_id=85000, end_id=95000, max_threads=50):
    scraped_ids = load_scraped_ids()
    logger.info(f"Loaded {len(scraped_ids)} already scraped Cricbuzz matches.")
    
    # Generate pending queue
    pending = [str(i) for i in range(start_id, end_id) if str(i) not in scraped_ids]
    logger.info(f"Prepared {len(pending)} pending Cricbuzz IDs to crawl.")
    
    if not pending:
        logger.info("No pending Cricbuzz IDs to crawl in this range.")
        return
        
    spider = CricbuzzSpider()
    success_count = 0
    
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {executor.submit(spider.fetch_match, mid): mid for mid in pending}
        
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
                        logger.info(f"Concurrently scraped {success_count} new Cricbuzz matches...")
            except Exception as e:
                pass

    logger.info(f"Cricbuzz crawl cycle complete. Successfully scraped {success_count} new matches.")

if __name__ == "__main__":
    # Start scanning from 1 to 105000 with 50 threads to capture ALL matches
    crawl_cricbuzz_range(start_id=1, end_id=105000, max_threads=50)
