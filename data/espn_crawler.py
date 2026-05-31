import os
import json
import time
import random
import logging
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor, as_completed

# Logger setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - ESPN CRAWLER - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_PATH = 'data/espn_history_db.jsonl'

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

def fetch_espn_match(match_id: str):
    # Cricinfo redirects if we use a placeholder series ID "s"
    url = f"https://www.espncricinfo.com/series/s/match/{match_id}/full-scorecard"
    
    try:
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # Navigate
            response = page.goto(url, wait_until="domcontentloaded", timeout=20000)
            
            if response and response.status == 200:
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                title_tag = soup.find('title')
                title = title_tag.text if title_tag else "Unknown Match"
                
                # Check if it has scorecard tables
                if "scorecard" in html.lower():
                    match_data = {
                        "source": "espn",
                        "match_id": str(match_id),
                        "title": title.strip(),
                        "url": url,
                        "status": "Scraped",
                        "timestamp": time.time()
                    }
                    browser.close()
                    return True, match_data
            
            browser.close()
            return False, None
    except Exception:
        return False, None

def crawl_espn_range(start_id=1300000, end_id=1310000, max_threads=4):
    scraped_ids = load_scraped_ids()
    logger.info(f"Loaded {len(scraped_ids)} already scraped ESPN matches.")
    
    # Generate pending queue
    pending = [str(i) for i in range(start_id, end_id) if str(i) not in scraped_ids]
    logger.info(f"Prepared {len(pending)} pending ESPN IDs to crawl.")
    
    if not pending:
        logger.info("No pending ESPN IDs to crawl in this range.")
        return
        
    success_count = 0
    
    # Since Playwright consumes resources, we limit to max_threads (e.g. 4)
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {executor.submit(fetch_espn_match, mid): mid for mid in pending}
        
        for future in as_completed(futures):
            mid = futures[future]
            try:
                success, data = future.result()
                if success and data:
                    with open(DB_PATH, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(data, ensure_ascii=False) + '\n')
                    success_count += 1
                    logger.info(f"Scraped new ESPN match: {mid} - {data['title'][:60]}")
            except Exception as e:
                pass

if __name__ == "__main__":
    # Start scanning from 1300000 to 1310000 with 4 Playwright workers
    crawl_espn_range(start_id=1300000, end_id=1310000, max_threads=4)
