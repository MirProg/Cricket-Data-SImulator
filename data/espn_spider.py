import os
import time
import json
import random
import logging
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - ESPN PLAYWRIGHT SPIDER - %(levelname)s - %(message)s')

class ESPNHistoricalSpider:
    def __init__(self):
        self.data_dir = os.path.dirname(__file__)
        self.db_path = os.path.join(self.data_dir, 'espn_history_db.jsonl')
        
    def fetch_match(self, series_id: str, match_id: str):
        """
        Fetches the full scorecard and commentary for a specific historical match
        using a Headless Chromium browser to bypass Cloudflare.
        """
        url = f"https://www.espncricinfo.com/series/{series_id}/match/{match_id}/full-scorecard"
        
        logger.info(f"Stealth fetching via Playwright: {url}")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                
                # Navigate and wait for DOM and Cloudflare checks to finish
                response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                if response and response.status == 200:
                    html_content = page.content()
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Extract basic match title
                    title_tag = soup.find('title')
                    title = title_tag.text if title_tag else "Unknown Match"
                    
                    match_data = {
                        "match_id": match_id,
                        "series_id": series_id,
                        "title": title,
                        "url": url,
                        "status": "Scraped",
                        "timestamp": time.time()
                    }
                    
                    self.save_match(match_data)
                    browser.close()
                    return True
                else:
                    status = response.status if response else "Unknown"
                    logger.error(f"Failed to fetch {url}. Status: {status}")
                    browser.close()
                    return False
                    
        except Exception as e:
            logger.error(f"Exception during Playwright fetch: {e}")
            return False
            
    def save_match(self, match_data: dict):
        """Append to JSON Lines file to handle millions of matches without memory issues."""
        with open(self.db_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(match_data) + '\n')
            
    def crawl_history(self):
        """
        The main loop that Claude AI will run.
        It simulates human browsing by sleeping 30-45 seconds between requests.
        """
        logger.info("Starting Playwright Slow-Drip Historical Spider (1 match / 30s)...")
        
        match_queue = [
            ("60399", "62431"), # 1st Test 1877
            ("60400", "62432"), # 2nd Test 1877
        ]
        
        for series_id, match_id in match_queue:
            success = self.fetch_match(series_id, match_id)
            if success:
                logger.info(f"Successfully scraped {match_id}. Sleeping to evade detection...")
            
            # Sleep 30-45 seconds to mimic human reading speed and avoid IP ban
            sleep_time = random.uniform(30.0, 45.0)
            time.sleep(sleep_time)

if __name__ == "__main__":
    spider = ESPNHistoricalSpider()
    spider.crawl_history()
