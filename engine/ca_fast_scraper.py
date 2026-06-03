import asyncio
import aiohttp
import sqlite3
import logging
from bs4 import BeautifulSoup
import argparse
import browser_cookie3

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# We automatically extract your active Firefox session cookies so you don't have to copy-paste them!
try:
    print("Extracting Firefox cookies...")
    cj = browser_cookie3.firefox(domain_name='cricketarchive.com')
    print("Cookies extracted successfully!")
except Exception as e:
    print(f"Failed to extract Firefox cookies: {e}")
    cj = None

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

DB_PATH = r"C:\Users\seo\.local\bin\cricket_simulator\data\master_archive.sqlite"

async def fetch_scorecard(session, match_id):
    """
    CricketArchive Scorecard URL format is typically:
    https://cricketarchive.com/Archive/Scorecards/{folder}/{match_id}.html
    For this engine, we will assume a direct routing or search mechanism.
    """
    url = f"https://cricketarchive.com/Archive/Scorecards/{match_id // 1000}/{match_id}.html"
    try:
        async with session.get(url, headers=HEADERS, timeout=10) as response:
            if response.status == 200:
                html = await response.text()
                return match_id, html
            else:
                logging.warning(f"Match {match_id} returned status {response.status}")
                return match_id, None
    except Exception as e:
        logging.error(f"Error fetching {match_id}: {e}")
        return match_id, None

def process_and_save_html(match_id, html_content):
    """
    Save the raw HTML to the DB instantly.
    """
    if not html_content: return
    
    with sqlite3.connect(DB_PATH, timeout=30) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS RawHTML (match_id INTEGER PRIMARY KEY, html TEXT)")
        conn.execute("INSERT OR REPLACE INTO RawHTML (match_id, html) VALUES (?, ?)", (match_id, html_content))
    
    logging.info(f"Downloaded Match {match_id}")

async def worker(queue, session):
    while True:
        match_id = await queue.get()
        _, html = await fetch_scorecard(session, match_id)
        if html:
            # Offload parsing/saving to synchronous function
            process_and_save_html(match_id, html)
        queue.task_done()

async def main(start_id, end_id, concurrency):
    logging.info(f"Starting FULL SPEED scrape from {start_id} to {end_id} with {concurrency} workers.")
    
    queue = asyncio.Queue()
    for m_id in range(start_id, end_id + 1):
        queue.put_nowait(m_id)
        
    # Convert browser_cookie3 cookiejar to dictionary
    cookie_dict = {}
    if cj:
        for cookie in cj:
            cookie_dict[cookie.name] = cookie.value
        
    async with aiohttp.ClientSession(cookies=cookie_dict) as session:
        tasks = []
        for _ in range(concurrency):
            task = asyncio.create_task(worker(queue, session))
            tasks.append(task)
            
        await queue.join()
        
        for task in tasks:
            task.cancel()
            
    logging.info("High-Speed Scraping Complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CricketArchive High-Speed Scraper")
    parser.add_argument("--start", type=int, default=100000, help="Starting Match ID")
    parser.add_argument("--end", type=int, default=100100, help="Ending Match ID")
    parser.add_argument("--workers", type=int, default=50, help="Number of concurrent connections")
    
    args = parser.parse_args()
    
    # Run the async event loop
    asyncio.run(main(args.start, args.end, args.workers))
