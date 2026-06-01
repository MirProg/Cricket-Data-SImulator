import sqlite3
import os
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - SYNC - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = 'data/cricket_db.sqlite'
RAW_DATA_DIR = Path('data/raw_ca')

def sync_queue():
    logger.info("Connecting to database to sync CrawlQueue...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all SUCCESS rows
    cursor.execute("SELECT ca_match_id FROM CrawlQueue WHERE status='SUCCESS'")
    success_rows = cursor.fetchall()
    
    logger.info(f"Found {len(success_rows)} matches marked as SUCCESS. Verifying physical HTML files...")
    
    missing_ids = []
    for row in success_rows:
        match_id = row[0]
        file_path = RAW_DATA_DIR / f"{match_id}.html"
        if not file_path.exists():
            missing_ids.append(match_id)
            
    if not missing_ids:
        logger.info("All SUCCESS rows have matching HTML files. No sync needed!")
        conn.close()
        return

    logger.info(f"Found {len(missing_ids)} missing HTML files! Requeuing to PENDING...")
    
    # Bulk update back to PENDING in chunks to prevent locking
    chunk_size = 5000
    for i in range(0, len(missing_ids), chunk_size):
        chunk = missing_ids[i:i+chunk_size]
        update_data = [('PENDING', m_id) for m_id in chunk]
        
        retries = 5
        while retries > 0:
            try:
                # Open a short-lived connection per chunk
                conn = sqlite3.connect(DB_PATH, timeout=30.0)
                conn.execute('PRAGMA journal_mode=WAL;')
                cursor = conn.cursor()
                cursor.executemany("UPDATE CrawlQueue SET status=? WHERE ca_match_id=?", update_data)
                conn.commit()
                conn.close()
                break
            except sqlite3.OperationalError:
                retries -= 1
                import time
                time.sleep(2)
        logger.info(f"Requeued chunk {i} to {i+len(chunk)}")
    
    logger.info(f"Successfully requeued {len(missing_ids)} matches. Ready for async_scraper.py to blast through them!")

if __name__ == "__main__":
    sync_queue()
