import requests
import logging
from bs4 import BeautifulSoup
import json
import os

logger = logging.getLogger(__name__)

class CricketArchiveSpider:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive'
        }
        
    def fetch_match(self, match_id: str) -> bool:
        """
        Fetches the match scorecard from CricketArchive.
        By bypassing Javascript execution entirely, we bypass the Pigeon Paywall 
        that hides the HTML content on the client side.
        """
        url = f"https://cricketarchive.com/Archive/Scorecards/{match_id[:4]}/{match_id}.html"
        logger.info(f"Fetching from CricketArchive: {url}")
        
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            # Since requests doesn't execute JS, the Pigeon paywall is completely neutralized.
            # The scorecard tables are present in the raw HTML.
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check if scorecard data actually exists
            tables = soup.find_all('table')
            if len(tables) < 2:
                logger.error("CricketArchive returned unexpected HTML structure. Paywall might have upgraded.")
                return False
                
            logger.info(f"CricketArchive Paywall bypassed! Successfully retrieved scorecard HTML for {match_id}")
            
            # Save raw html for processing
            os.makedirs("data/raw_ca", exist_ok=True)
            with open(f"data/raw_ca/{match_id}.html", "w", encoding="utf-8") as f:
                f.write(response.text)
                
            # Log success into the unified dataset manifest
            with open("data/cricbuzz_history_db.jsonl", "a", encoding="utf-8") as f:
                json.dump({"source": "cricketarchive", "id": match_id, "status": "scraped_raw_html", "tables": len(tables)}, f)
                f.write("\n")
                
            return True
            
        except Exception as e:
            logger.error(f"CricketArchive Spider failed for {match_id}: {e}")
            return False
