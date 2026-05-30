import os
import time
import json
import random
import logging
import cloudscraper
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - ESPN SPIDER - %(levelname)s - %(message)s')

class ESPNHistoricalSpider:
    def __init__(self):
        # cloudscraper mimics a real browser to bypass 403 Forbidden / Cloudflare blocks
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
        self.data_dir = os.path.dirname(__file__)
        self.db_path = os.path.join(self.data_dir, 'espn_history_db.jsonl')
        
    def fetch_match(self, series_id: str, match_id: str):
        """
        Fetches the full scorecard and commentary for a specific historical match.
        Example Test Match 1877: series_id="60399", match_id="62431" (England vs Aus)
        """
        url = f"https://www.espncricinfo.com/series/{series_id}/match/{match_id}/full-scorecard"
        
        logger.info(f"Stealth fetching historical match: {url}")
        try:
            response = self.scraper.get(url, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract basic match title
                title_tag = soup.find('title')
                title = title_tag.text if title_tag else "Unknown Match"
                
                # In a full run, we would parse all <div> elements for exact commentary,
                # wickets, and ball-by-ball. This is a skeleton that demonstrates the bypass.
                
                match_data = {
                    "match_id": match_id,
                    "series_id": series_id,
                    "title": title,
                    "url": url,
                    "status": "Scraped",
                    "timestamp": time.time()
                }
                
                self.save_match(match_data)
                return True
            else:
                logger.error(f"Failed to fetch {url}. Status: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Exception during fetch: {e}")
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
        logger.info("Starting Slow-Drip Historical Spider (1 match / 30s)...")
        
        # In a real run, this would be a queue of millions of match IDs dating back to 1877.
        # For demonstration, we scrape the first Test Match in history.
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
