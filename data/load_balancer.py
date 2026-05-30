import logging
import random
import time
import os
from espn_spider import ESPNHistoricalSpider
from cricbuzz_spider import CricbuzzSpider
from cricketarchive_spider import CricketArchiveSpider

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
        self.cricketarchive = CricketArchiveSpider()
        
    def fetch_historical_match(self, espn_series: str, espn_match: str, cb_match: str):
        """
        Dynamically load-balances the request.
        If ESPN fails (403 block), it automatically fails over to Cricbuzz.
        """
        # We route traffic between CricketArchive, Cricbuzz, and ESPN
        route = random.random()
        
        if route < 0.33:
            logger.info("Routing request to CRICKETARCHIVE Spider...")
            success = self.cricketarchive.fetch_match(cb_match) # just using cb_match as id for now or pass ca_match
            if not success:
                logger.warning("CricketArchive failed. Failing over to CRICBUZZ Spider...")
                success = self.cricbuzz.fetch_match(cb_match)
        elif route < 0.66:
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
        import sqlite3
        logger.info("Starting Distributed Scraper Engine with SQLite Queue (ESPN + Cricbuzz + CricketArchive)")
        
        conn = sqlite3.connect('data/cricket_db.sqlite')
        
        while True:
            # Fetch up to 10 pending matches per chunk
            cursor = conn.execute("SELECT ca_match_id FROM CrawlQueue WHERE status='PENDING' LIMIT 10")
            pending_matches = cursor.fetchall()
            
            if not pending_matches:
                logger.info("CrawlQueue is empty! No pending matches found.")
                break
                
            for (ca_id,) in pending_matches:
                # We rely entirely on CricketArchive! (Which the user noted has no limits!)
                logger.info(f"Routing request exclusively to CRICKETARCHIVE Spider for ID: {ca_id}...")
                success = self.cricketarchive.fetch_match(ca_id)
                
                if success:
                    conn.execute("UPDATE CrawlQueue SET status='COMPLETED' WHERE ca_match_id=?", (ca_id,))
                else:
                    conn.execute("UPDATE CrawlQueue SET status='FAILED' WHERE ca_match_id=?", (ca_id,))
                    
                conn.commit()
                
                # FULL THROTTLE: The user requested no cooldowns for CricketArchive
                
        conn.close()

if __name__ == "__main__":
    engine = DistributedScraperEngine()
    engine.run_distributed_crawl()
