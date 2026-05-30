import logging
import random
import time
import os
from espn_spider import ESPNHistoricalSpider
from cricbuzz_spider import CricbuzzSpider

logger = logging.getLogger(__name__)

# Ensure data dir exists
os.makedirs("data", exist_ok=True)

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - LOAD BALANCER - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data/scraper.log", mode="a", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

class DistributedScraperEngine:
    def __init__(self):
        self.espn = ESPNHistoricalSpider()
        self.cricbuzz = CricbuzzSpider()
        
    def fetch_historical_match(self, espn_series: str, espn_match: str, cb_match: str):
        """
        Dynamically load-balances the request.
        If ESPN fails (403 block), it automatically fails over to Cricbuzz.
        """
        # We route 60% of requests to Cricbuzz naturally to protect the ESPN IP
        route = random.random()
        
        if route < 0.6:
            logger.info("Routing request to CRICBUZZ Spider...")
            success = self.cricbuzz.fetch_match(cb_match)
            if not success:
                logger.warning("Cricbuzz failed. Failing over to ESPN Spider...")
                success = self.espn.fetch_match(espn_series, espn_match)
        else:
            logger.info("Routing request to ESPN Spider...")
            success = self.espn.fetch_match(espn_series, espn_match)
            if not success:
                logger.warning("ESPN failed (likely 403 Cloudflare block). Failing over to CRICBUZZ Spider...")
                success = self.cricbuzz.fetch_match(cb_match)
                
        return success
        
    def run_distributed_crawl(self):
        logger.info("Starting Distributed Scraper Engine (ESPN + Cricbuzz)")
        
        # A mapped queue of matches
        match_queue = [
            # 2011 World Cup Final: ESPN ID vs Cricbuzz ID
            {"espn_series": "381449", "espn_match": "433606", "cb_match": "10672"},
            # Random IPL match
            {"espn_series": "8048", "espn_match": "1422127", "cb_match": "89736"},
        ]
        
        for match in match_queue:
            self.fetch_historical_match(match["espn_series"], match["espn_match"], match["cb_match"])
            
            # Global Sleep to protect IP
            sleep_time = random.uniform(25.0, 40.0)
            logger.info(f"Cooling down for {sleep_time:.1f} seconds to evade WAFs...")
            time.sleep(sleep_time)

if __name__ == "__main__":
    engine = DistributedScraperEngine()
    engine.run_distributed_crawl()
