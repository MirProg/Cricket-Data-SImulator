import os
import time
import json
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - CRICBUZZ SPIDER - %(levelname)s - %(message)s')

class CricbuzzSpider:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.data_dir = os.path.dirname(__file__)
        self.db_path = os.path.join(self.data_dir, 'cricbuzz_history_db.jsonl')
        
    def fetch_match(self, match_id: str):
        """
        Fetches the scorecard and commentary from Cricbuzz.
        Cricbuzz URL format: https://www.cricbuzz.com/live-cricket-scorecard/{match_id}/
        """
        url = f"https://www.cricbuzz.com/live-cricket-scorecard/{match_id}/"
        
        logger.info(f"Fetching from Cricbuzz: {url}")
        
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                title_tag = soup.find('title')
                title = title_tag.text if title_tag else "Unknown Match"
                
                match_data = {
                    "source": "cricbuzz",
                    "match_id": match_id,
                    "title": title,
                    "url": url,
                    "status": "Scraped",
                    "timestamp": time.time()
                }
                
                self.save_match(match_data)
                return True
            else:
                logger.warning(f"Failed to fetch {url}. Status: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Exception during Cricbuzz fetch: {e}")
            return False
            
    def save_match(self, match_data: dict):
        with open(self.db_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(match_data) + '\n')

if __name__ == "__main__":
    spider = CricbuzzSpider()
    # Test fetch for a known Cricbuzz match
    spider.fetch_match("35630") # Example random Cricbuzz match ID
