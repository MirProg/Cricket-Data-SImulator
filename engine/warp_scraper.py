"""
High-Speed CricketArchive Scraper with Cloudflare WARP VPN Toggling
- Uses aiohttp for extreme parallel downloading
- If Cloudflare blocks (403 Forbidden), it pauses, toggles WARP to get a new IP,
  reloads Firefox cookies via browser_cookie3, and resumes instantly.
"""

import asyncio
import aiohttp
import sqlite3
import subprocess
import time
import logging
import argparse
import browser_cookie3
from bs4 import BeautifulSoup
import re
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

DB_PATH = r"C:\Users\seo\.local\bin\cricket_simulator\data\master_archive.sqlite"
MAX_WORKERS = 50
RETRY_DELAY = 1.0

# Global lock to prevent multiple workers from toggling VPN simultaneously
VPN_LOCK = asyncio.Lock()

def toggle_vpn():
    """Toggle Cloudflare WARP VPN to get a new IP address."""
    logging.info(">>> DETECTED CLOUDFLARE BLOCK (403). TOGGLING VPN FOR NEW IP... <<<")
    try:
        subprocess.run(["warp-cli", "disconnect"], check=True, capture_output=True)
        time.sleep(2)
        subprocess.run(["warp-cli", "connect"], check=True, capture_output=True)
        time.sleep(4)  # Give it a few seconds to establish connection
        logging.info(">>> VPN TOGGLED SUCCESSFULLY. Resuming... <<<")
        return True
    except Exception as e:
        logging.error(f"Failed to toggle VPN: {e}")
        return False

def get_cookies():
    """Extract CricketArchive cookies from Firefox."""
    try:
        cj = browser_cookie3.firefox()
        cookies = {}
        for c in cj:
            if "cricketarchive" in c.domain:
                cookies[c.name] = c.value
        return cookies
    except Exception as e:
        logging.error(f"Error extracting cookies: {e}")
        return {}

def ensure_tables(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS ScrapedMatches (
            match_id INTEGER PRIMARY KEY,
            title TEXT,
            series TEXT,
            venue TEXT,
            date_text TEXT,
            format TEXT,
            toss TEXT,
            result TEXT,
            balls_per_over TEXT
        );
        CREATE TABLE IF NOT EXISTS ScrapedInnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER,
            innings_number INTEGER,
            batting_team TEXT,
            total_runs INTEGER,
            total_wickets INTEGER,
            total_overs TEXT,
            FOREIGN KEY(match_id) REFERENCES ScrapedMatches(match_id)
        );
        CREATE TABLE IF NOT EXISTS ScrapedBatting (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER,
            innings_number INTEGER,
            player_name TEXT,
            dismissal TEXT,
            runs INTEGER,
            balls TEXT,
            mins TEXT,
            fours TEXT,
            sixes TEXT,
            FOREIGN KEY(match_id) REFERENCES ScrapedMatches(match_id)
        );
        CREATE TABLE IF NOT EXISTS ScrapedBowling (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER,
            innings_number INTEGER,
            player_name TEXT,
            overs TEXT,
            maidens TEXT,
            runs INTEGER,
            wickets INTEGER,
            wides TEXT,
            no_balls TEXT,
            FOREIGN KEY(match_id) REFERENCES ScrapedMatches(match_id)
        );
        CREATE TABLE IF NOT EXISTS ScrapeProgress (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)

def parse_scorecard(html, match_id, conn):
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")
    
    if len(tables) < 2:
        return False
        
    meta_table = tables[0]
    meta_rows = meta_table.find_all("tr")
    
    title = ""
    series = ""
    venue = ""
    date_text = ""
    fmt = ""
    toss = ""
    result = ""
    balls_per_over = ""
    
    for row in meta_rows:
        cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
        if len(cells) >= 2:
            label = cells[0].lower()
            value = cells[1]
            if "venue" in label or "lord" in value.lower() or "ground" in value.lower() or "on " in value.lower():
                venue = value
            elif "toss" in label: toss = value
            elif "balls per over" in label: balls_per_over = value
            elif "result" in label: result = value
            elif not title: title = value
            elif not series: series = value
    
    conn.execute("""
        INSERT OR REPLACE INTO ScrapedMatches 
        (match_id, title, series, venue, date_text, format, toss, result, balls_per_over)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (match_id, title, series, venue, date_text, fmt, toss, result, balls_per_over))
    
    innings_num = 0
    i = 1  
    
    while i < len(tables):
        table = tables[i]
        first_row = table.find("tr")
        if not first_row:
            i += 1
            continue
            
        header_cells = [c.get_text(strip=True) for c in first_row.find_all(["td", "th"])]
        header_text = header_cells[0] if header_cells else ""
        
        if "innings" in header_text.lower():
            innings_num += 1
            batting_team = re.sub(r'(first|second|third|fourth)\s*innings', '', header_text, flags=re.IGNORECASE).strip()
            
            rows = table.find_all("tr")[1:]
            total_runs = 0
            total_wickets = 0
            
            for row in rows:
                cells = [c.get_text(strip=True) for c in row.find_all("td")]
                if len(cells) < 3: continue
                
                player_name = cells[0]
                if not player_name or player_name.lower() in ['extras', 'total', '']:
                    if 'total' in player_name.lower() and len(cells) >= 3:
                        try: total_runs = int(re.sub(r'[^\d]', '', cells[2])) if cells[2] else 0
                        except: pass
                    continue
                
                dismissal = cells[1] if len(cells) > 1 else ""
                runs = 0
                try: runs = int(cells[2]) if len(cells) > 2 and cells[2].isdigit() else 0
                except: pass
                
                balls = cells[3] if len(cells) > 3 else ""
                mins = cells[4] if len(cells) > 4 else ""
                fours = cells[5] if len(cells) > 5 else ""
                sixes = cells[6] if len(cells) > 6 else ""
                
                if dismissal and dismissal != "did not bat" and "not out" not in dismissal:
                    total_wickets += 1
                
                conn.execute("""
                    INSERT INTO ScrapedBatting 
                    (match_id, innings_number, player_name, dismissal, runs, balls, mins, fours, sixes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (match_id, innings_num, player_name, dismissal, runs, balls, mins, fours, sixes))
            
            conn.execute("""
                INSERT INTO ScrapedInnings
                (match_id, innings_number, batting_team, total_runs, total_wickets, total_overs)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (match_id, innings_num, batting_team, total_runs, total_wickets, ""))
            i += 1
            
        elif "bowling" in header_text.lower():
            rows = table.find_all("tr")[1:]
            for row in rows:
                cells = [c.get_text(strip=True) for c in row.find_all("td")]
                if len(cells) < 5 or not cells[0]: continue
                
                player_name = cells[0]
                overs = cells[1] if len(cells) > 1 else ""
                maidens = cells[2] if len(cells) > 2 else ""
                runs = 0
                try: runs = int(cells[3]) if len(cells) > 3 and cells[3].isdigit() else 0
                except: pass
                wickets = 0
                try: wickets = int(cells[4]) if len(cells) > 4 and cells[4].isdigit() else 0
                except: pass
                wides = cells[5] if len(cells) > 5 else ""
                no_balls = cells[6] if len(cells) > 6 else ""
                
                conn.execute("""
                    INSERT INTO ScrapedBowling
                    (match_id, innings_number, player_name, overs, maidens, runs, wickets, wides, no_balls)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (match_id, innings_num, player_name, overs, maidens, runs, wickets, wides, no_balls))
            i += 1
        else:
            i += 1
    
    conn.commit()
    return True

async def fetch_match(session, match_id, conn, sem):
    async with sem:
        url = f"https://cricketarchive.com/Archive/Scorecards/{match_id // 1000}/{match_id}.html"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        
        while True:
            try:
                async with session.get(url, headers=headers, timeout=20) as response:
                    # If Cloudflare blocks us, we get a 403
                    if response.status == 403:
                        async with VPN_LOCK:
                            # Toggling the VPN fixes the 403 instantly for everyone
                            logging.info(f"Worker hit 403 on ID {match_id}")
                            toggle_vpn()
                            # After toggling, we must reload cookies and update session
                            session.cookie_jar.clear()
                            session.cookie_jar.update_cookies(get_cookies())
                        await asyncio.sleep(RETRY_DELAY)
                        continue # Retry the request
                    
                    if response.status != 200:
                        return False

                    html = await response.text()
                    
                    if "Access Denied" in html:
                        async with VPN_LOCK:
                            logging.info(f"Worker hit Access Denied on ID {match_id}")
                            toggle_vpn()
                            session.cookie_jar.clear()
                            session.cookie_jar.update_cookies(get_cookies())
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                        
                    parsed = parse_scorecard(html, match_id, conn)
                    return parsed
            except asyncio.TimeoutError:
                await asyncio.sleep(RETRY_DELAY)
                continue
            except Exception as e:
                return False

def get_last_scraped(conn):
    row = conn.execute("SELECT value FROM ScrapeProgress WHERE key='last_match_id'").fetchone()
    return int(row[0]) if row else 0

def save_progress(conn, match_id):
    conn.execute("INSERT OR REPLACE INTO ScrapeProgress (key, value) VALUES ('last_match_id', ?)", (str(match_id),))
    conn.commit()

async def run_scraper(start_id, end_id, max_workers):
    logging.info("Connecting to Database...")
    conn = sqlite3.connect(DB_PATH, timeout=60, isolation_level=None)
    ensure_tables(conn)
    
    last = get_last_scraped(conn)
    if last > 0 and start_id <= last:
        start_id = last + 1
        logging.info(f"Resuming from match ID {start_id}")
    
    logging.info("Extracting initial Firefox Cookies...")
    cookies = get_cookies()
    
    sem = asyncio.Semaphore(max_workers)
    
    async with aiohttp.ClientSession(cookies=cookies) as session:
        success = 0
        
        # We will dispatch in batches to avoid eating up all memory
        BATCH_SIZE = 1000
        for batch_start in range(start_id, end_id + 1, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE - 1, end_id)
            tasks = []
            
            for match_id in range(batch_start, batch_end + 1):
                tasks.append(fetch_match(session, match_id, conn, sem))
                
            results = await asyncio.gather(*tasks)
            
            for parsed in results:
                if parsed: success += 1
                
            save_progress(conn, batch_end)
            logging.info(f"Finished batch {batch_start}-{batch_end}. Total successful parsed: {success}")

    conn.close()
    logging.info(f"COMPLETE. Total scorecards parsed: {success}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=900000)
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    args = parser.parse_args()
    
    logging.info(f"Starting High-Speed WARP Scraper (Workers: {args.workers})")
    asyncio.run(run_scraper(args.start, args.end, args.workers))
