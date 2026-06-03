"""
CricketArchive Playwright Scraper
- Uses a REAL Firefox browser so Cloudflare cannot distinguish it from your normal browsing
- Parses scorecards directly into SQL (no raw HTML stored)
- Supports resuming from where it left off
- Injects native Firefox cookies to bypass paywall instantly
"""
import sqlite3
import re
import time
import argparse
import browser_cookie3
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import sys

def log(msg):
    print(msg)
    sys.stdout.flush()

DB_PATH = r"C:\Users\seo\.local\bin\cricket_simulator\data\master_archive.sqlite"

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
    """Parse CricketArchive HTML scorecard directly into SQL tables."""
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    
    if len(tables) < 2:
        log(f"Match {match_id}: Not a scorecard page (only {len(tables)} tables)")
        return False
    
    # Table 0 = Match metadata
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
            elif "toss" in label:
                toss = value
            elif "balls per over" in label:
                balls_per_over = value
            elif "result" in label:
                result = value
            elif not title:
                title = value
            elif not series:
                series = value
    
    conn.execute("""
        INSERT OR REPLACE INTO ScrapedMatches 
        (match_id, title, series, venue, date_text, format, toss, result, balls_per_over)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (match_id, title, series, venue, date_text, fmt, toss, result, balls_per_over))
    
    # Parse innings tables
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
                if len(cells) < 3:
                    continue
                
                player_name = cells[0]
                if not player_name or player_name.lower() in ['extras', 'total', '']:
                    if 'total' in player_name.lower() and len(cells) >= 3:
                        try:
                            total_runs = int(re.sub(r'[^\d]', '', cells[2])) if cells[2] else 0
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
                
                if dismissal and dismissal != "did not bat":
                    if "not out" not in dismissal:
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
                if len(cells) < 5 or not cells[0]:
                    continue
                
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

def get_last_scraped(conn):
    row = conn.execute("SELECT value FROM ScrapeProgress WHERE key='last_match_id'").fetchone()
    return int(row[0]) if row else 0

def save_progress(conn, match_id):
    conn.execute("INSERT OR REPLACE INTO ScrapeProgress (key, value) VALUES ('last_match_id', ?)", (str(match_id),))
    conn.commit()

def run_scraper(start_id, end_id, delay):
    log("Connecting to Database...")
    conn = sqlite3.connect(DB_PATH, timeout=30)
    ensure_tables(conn)
    
    last = get_last_scraped(conn)
    if last > 0 and start_id <= last:
        start_id = last + 1
        log(f"Resuming from match ID {start_id}")
    
    log("Extracting Firefox Cookies...")
    try:
        cj = browser_cookie3.firefox()
        ca_cookies = [c for c in cj if "cricketarchive" in c.domain]
        log(f"Extracted {len(ca_cookies)} active Firefox cookies for CricketArchive")
    except Exception as e:
        log(f"Error extracting cookies: {e}")
        return
        
    pw_cookies = []
    for c in ca_cookies:
        pw_cookies.append({
            "name": c.name,
            "value": c.value,
            "domain": c.domain,
            "path": c.path,
        })
    
    with sync_playwright() as p:
        log("Launching headless Chromium...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        context.add_cookies(pw_cookies)
        page = context.new_page()
        
        success = 0
        errors = 0
        
        log(f"Starting loop from ID {start_id} to {end_id}")
        for match_id in range(start_id, end_id + 1):
            url = f"https://cricketarchive.com/Archive/Scorecards/{match_id // 1000}/{match_id}.html"
            
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
                html = page.content()
                
                if "Access Denied" in html or "403" in page.title():
                    log(f"Match {match_id}: BLOCKED (403/Cloudflare)")
                    errors += 1
                    time.sleep(delay * 2)
                    continue
                
                parsed = parse_scorecard(html, match_id, conn)
                if parsed:
                    success += 1
                    save_progress(conn, match_id)
                    if success % 10 == 0:
                        log(f"SUCCESS: Parsed {success} scorecards | Current ID: {match_id}")
                    
            except Exception as e:
                log(f"Match {match_id} ERROR: {str(e)[:100]}")
                errors += 1
            
            time.sleep(delay)
        
        browser.close()
    
    conn.close()
    log(f"COMPLETE. Total parsed: {success}, Total blocked: {errors}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=900000)
    parser.add_argument("--delay", type=float, default=0.3)
    args = parser.parse_args()
    
    run_scraper(args.start, args.end, args.delay)
