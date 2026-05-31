import sqlite3
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - DISCOVERY - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_db():
    conn = sqlite3.connect('data/cricket_db.sqlite')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS CrawlQueue (
            ca_match_id TEXT PRIMARY KEY,
            status TEXT DEFAULT 'PENDING',
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

def run_discovery():
    logger.info("Starting Massive Discovery Spider...")
    conn = setup_db()
    cursor = conn.cursor()
    
    # We will seed the queue with all possible CricketArchive Match IDs (1 to 1,500,000)
    # Using batch inserts for extreme performance
    
    BATCH_SIZE = 100000
    total_new = 0
    
    logger.info("Generating 1,500,000 match IDs...")
    
    start_time = time.time()
    
    for chunk_start in range(1, 1500001, BATCH_SIZE):
        chunk_end = min(chunk_start + BATCH_SIZE, 1500001)
        
        batch_data = [(str(i), 'PENDING') for i in range(chunk_start, chunk_end)]
        
        try:
            # INSERT OR IGNORE allows us to skip already queued matches instantly
            cursor.executemany('''
                INSERT OR IGNORE INTO CrawlQueue (ca_match_id, status) 
                VALUES (?, ?)
            ''', batch_data)
            conn.commit()
            
            inserted = cursor.rowcount
            total_new += inserted
            logger.info(f"Processed chunk {chunk_start} to {chunk_end-1}. Inserted new rows: {inserted}")
            
        except sqlite3.Error as e:
            logger.error(f"Database error during batch insert: {e}")
            conn.rollback()
            
    conn.close()
    
    elapsed = time.time() - start_time
    logger.info(f"Massive Discovery complete in {elapsed:.2f}s. Added {total_new} new matches to the CrawlQueue.")

if __name__ == "__main__":
    run_discovery()
