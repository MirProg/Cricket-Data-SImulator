import asyncio
import aiohttp
import sqlite3
import os
import logging
import time
import random
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - ASYNC_SCRAPER - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = 'data/cricket_db.sqlite'
RAW_DATA_DIR = Path('data/raw_ca')
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Scraper configuration
MAX_CONCURRENT_REQUESTS = 50
BATCH_SIZE = 5000

# User agents pool
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0'
]

async def fetch_match(session, match_id, semaphore):
    """Fetches a single match scorecard."""
    url = f"https://cricketarchive.com/Archive/Scorecards/{match_id[:4]}/{match_id}.html"
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Connection': 'keep-alive'
    }
    
    async with semaphore:
        # Minimal delay since VPN is active
        await asyncio.sleep(random.uniform(0.1, 0.3))
        try:
            async with session.get(url, headers=headers, timeout=20) as response:
                if response.status == 200:
                    text = await response.text()
                    # Check if it actually contains a scorecard table
                    if "<table" not in text:
                        return match_id, 'RETRY', None
                        
                    # Return HTML text directly in memory (ZERO DISK)
                    return match_id, 'SUCCESS', text
                    
                elif response.status == 404:
                    return match_id, 'FAILED_404', None
                elif response.status == 403:
                    return match_id, 'BANNED', None
                elif response.status == 429:
                    return match_id, 'RETRY_LATER', None
                else:
                    return match_id, 'RETRY', None
                    
        except asyncio.TimeoutError:
            return match_id, 'RETRY', None
        except Exception as e:
            err_str = str(e).lower()
            if "eof" in err_str or "connection" in err_str or "reset" in err_str:
                return match_id, 'RETRY', None
            return match_id, 'RETRY', None

def update_db_batch(results):
    """Synchronously bulk updates the database with crawl results and in-memory parsing."""
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    cursor = conn.cursor()
    
    update_data = [(status, match_id) for match_id, status, _ in results]
    
    try:
        cursor.executemany('''
            UPDATE CrawlQueue 
            SET status = ? 
            WHERE ca_match_id = ?
        ''', update_data)
        
        # Zero-disk in-memory parsing
        import parser
        for match_id, status, text in results:
            if status == 'SUCCESS' and text:
                try:
                    parsed_data = parser.parse_scorecard_html(text, match_id)
                    if parsed_data:
                        parser.save_parsed_match(conn, parsed_data)
                except Exception as e:
                    logger.error(f"Failed to parse match {match_id}: {e}")
                    
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to update database batch: {e}")
        conn.rollback()
    finally:
        conn.close()

async def scrape_batch(match_ids):
    """Scrape a batch of matches asynchronously."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    # Custom TCP connector to manage pools
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_REQUESTS, limit_per_host=MAX_CONCURRENT_REQUESTS)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_match(session, match_id, semaphore) for match_id in match_ids]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Clean results
        cleaned_results = []
        for i, r in enumerate(results):
            if isinstance(r, tuple) and len(r) == 3:
                cleaned_results.append(r)
            else:
                logger.error(f"Unhandled exception on match {match_ids[i]}: {r}")
                cleaned_results.append((match_ids[i], 'RETRY', None))
                
        return cleaned_results

def run_scraper(limit=None):
    """Main orchestrator function."""
    logger.info("Starting Hyper-Scalable Async Scraper...")
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    
    total_processed = 0
    
    while True:
        # Check if we reached the testing limit
        if limit and total_processed >= limit:
            logger.info(f"Reached configured limit of {limit} matches. Stopping.")
            break
            
        # Fetch pending matches
        cursor = conn.execute("SELECT ca_match_id FROM CrawlQueue WHERE status='PENDING' LIMIT ?", (BATCH_SIZE,))
        pending_rows = cursor.fetchall()
        
        if not pending_rows:
            logger.info("No more PENDING matches in the queue. Scrape complete!")
            break
            
        match_ids = [row[0] for row in pending_rows]
        logger.info(f"Fetched batch of {len(match_ids)} matches. Scraping...")
        
        start_time = time.time()
        
        # Run async scrape for this batch
        results = asyncio.run(scrape_batch(match_ids))
        
        elapsed = time.time() - start_time
        
        # Analyze results
        successes = sum(1 for _, status, _ in results if status == 'SUCCESS')
        failed_404 = sum(1 for _, status, _ in results if status == 'FAILED_404')
        banned = sum(1 for _, status, _ in results if status == 'BANNED')
        retries = sum(1 for _, status, _ in results if status.startswith('RETRY'))
        
        logger.info(f"Batch completed in {elapsed:.2f}s (Avg: {len(match_ids)/elapsed:.2f} req/s). " 
                    f"Success: {successes}, 404s: {failed_404}, Banned: {banned}, Retries: {retries}")
        
        # Write results back to DB
        update_db_batch(results)
        
        total_processed += len(match_ids)
        
        # Handle banning
        if banned > 0:
            logger.warning("Cloudflare 403 BAN detected! Halting scraper to prevent permanent blacklist.")
            logger.warning("You must implement IP rotation (e.g. Warp VPN) or delay execution.")
            break
            
    conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Async CricketArchive Scraper")
    parser.add_argument("--benchmark", action="store_true", help="Run a benchmark test on 5,000 matches")
    args = parser.parse_args()
    
    if args.benchmark:
        logger.info("Running Benchmark Mode (Limit: 5000)")
        run_scraper(limit=5000)
    else:
        run_scraper()
