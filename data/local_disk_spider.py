"""
Local Disk Spider - reads CricketArchive scorecards from the local mirror at D:\\cricketarchive.com
instead of hitting the network. This is infinitely faster and immune to IP bans.
"""
import os
import json
import logging
import sqlite3
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - LOCAL DISK SPIDER - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data/scraper.log", mode="a", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

LOCAL_MIRROR = r"D:\cricketarchive.com\Archive\Scorecards"
DB_PATH = "data/cricket_db.sqlite"

def setup_db():
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS CrawlQueue (
            ca_match_id TEXT PRIMARY KEY,
            status TEXT DEFAULT 'PENDING',
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

def discover_local_files():
    """Scan the local mirror and inject every scorecard into the CrawlQueue."""
    logger.info(f"Scanning local mirror at {LOCAL_MIRROR}...")
    conn = setup_db()
    
    new_matches = 0
    total_files = 0
    
    for subdir in os.listdir(LOCAL_MIRROR):
        subdir_path = os.path.join(LOCAL_MIRROR, subdir)
        if not os.path.isdir(subdir_path):
            continue
        for filename in os.listdir(subdir_path):
            if not filename.endswith('.html'):
                continue
            match_id = filename.replace('.html', '')
            total_files += 1
            try:
                conn.execute('INSERT INTO CrawlQueue (ca_match_id, status) VALUES (?, ?)', (match_id, 'LOCAL_PENDING'))
                new_matches += 1
            except sqlite3.IntegrityError:
                pass
    
    conn.commit()
    logger.info(f"Scan complete. Found {total_files} files. Injected {new_matches} new matches into CrawlQueue.")
    return conn

def process_scorecard(match_id):
    """Parse a single scorecard HTML from the local disk."""
    # Figure out the subdirectory (first 4 digits of the match_id)
    subdir = match_id[:4] if len(match_id) > 4 else match_id[:3]
    filepath = os.path.join(LOCAL_MIRROR, subdir, f"{match_id}.html")
    
    if not os.path.exists(filepath):
        # Try other subdirectories
        for d in os.listdir(LOCAL_MIRROR):
            candidate = os.path.join(LOCAL_MIRROR, d, f"{match_id}.html")
            if os.path.exists(candidate):
                filepath = candidate
                break
        else:
            return match_id, False, "File not found"
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            html = f.read()
        
        soup = BeautifulSoup(html, 'html.parser')
        tables = soup.find_all('table')
        
        if len(tables) < 2:
            return match_id, False, "No scorecard tables found"
        
        # Save to our processed data directory
        os.makedirs("data/raw_ca", exist_ok=True)
        # Copy the file to our raw_ca directory
        with open(f"data/raw_ca/{match_id}.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        return match_id, True, f"{len(tables)} tables"
    except Exception as e:
        return match_id, False, str(e)

def run_local_ingest():
    """Main function: discover local files and process them at maximum speed."""
    conn = discover_local_files()
    
    cursor = conn.execute("SELECT ca_match_id FROM CrawlQueue WHERE status='LOCAL_PENDING'")
    pending = cursor.fetchall()
    
    if not pending:
        logger.info("No LOCAL_PENDING matches found. Waiting for more files to appear...")
        conn.close()
        return 0
    
    logger.info(f"Processing {len(pending)} local scorecards with 10 threads...")
    
    completed = 0
    failed = 0
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_scorecard, mid[0]): mid[0] for mid in pending}
        
        for future in as_completed(futures):
            match_id, success, detail = future.result()
            if success:
                conn.execute("UPDATE CrawlQueue SET status='COMPLETED' WHERE ca_match_id=?", (match_id,))
                completed += 1
            else:
                conn.execute("UPDATE CrawlQueue SET status='FAILED' WHERE ca_match_id=?", (match_id,))
                failed += 1
    
    conn.commit()
    conn.close()
    logger.info(f"Local ingest complete. Completed: {completed}, Failed: {failed}")
    return completed

def run_continuous():
    """Continuously scan for new files as the website download progresses."""
    logger.info("Starting CONTINUOUS local disk ingest mode...")
    logger.info(f"Monitoring: {LOCAL_MIRROR}")
    
    while True:
        processed = run_local_ingest()
        logger.info(f"Cycle done. Processed {processed} files. Sleeping 30s before next scan...")
        time.sleep(30)

if __name__ == "__main__":
    run_continuous()
