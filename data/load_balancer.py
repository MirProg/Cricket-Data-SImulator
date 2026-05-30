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
        
        conn = sqlite3.connect('data/cricket_db.sqlite', check_same_thread=False)
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        
        db_lock = threading.Lock()
        
        while True:
            # Fetch up to 20 pending matches per chunk
            cursor = conn.execute("SELECT ca_match_id FROM CrawlQueue WHERE status='PENDING' LIMIT 20")
            pending_matches = cursor.fetchall()
            
            if not pending_matches:
                logger.info("CrawlQueue is empty! No pending matches found.")
                break
                
            logger.info(f"Dispatching {len(pending_matches)} matches to ThreadPoolExecutor (5 threads)...")
            
            def scrape_worker(ca_id):
                success = self.cricketarchive.fetch_match(ca_id)
                return ca_id, success
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(scrape_worker, ca_id[0]): ca_id[0] for ca_id in pending_matches}
                
                for future in as_completed(futures):
                    ca_id, success = future.result()
                    with db_lock:
                        if success:
                            conn.execute("UPDATE CrawlQueue SET status='COMPLETED' WHERE ca_match_id=?", (ca_id,))
                        else:
                            conn.execute("UPDATE CrawlQueue SET status='FAILED' WHERE ca_match_id=?", (ca_id,))
                        
            # Commit the entire batch
            conn.commit()
            logger.info("Batch processed and committed.")
            
            # Small cooldown between batches to avoid triggering Cloudflare again
            time.sleep(2)
            
        conn.close()

if __name__ == "__main__":
    engine = DistributedScraperEngine()
    engine.run_distributed_crawl()
