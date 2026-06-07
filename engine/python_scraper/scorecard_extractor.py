import sqlite3
import os
import time
import re
import subprocess
import threading
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from curl_cffi import requests
import browser_cookie3
import queue

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "master_archive.sqlite"))
MAX_WORKERS = 40

ip_rotation_lock = threading.Lock()
error_count = 0

def toggle_cloudflare():
    global error_count
    try:
        print("\n[IP-ROTATION] Toggling Cloudflare WARP to cycle IP...")
        subprocess.run(["warp-cli", "disconnect"], check=True, capture_output=True, timeout=10)
        time.sleep(2)
        subprocess.run(["warp-cli", "connect"], check=True, capture_output=True, timeout=10)
        time.sleep(5) # Wait for network to stabilize
        print("[IP-ROTATION] IP Cycled successfully.\n")
    except Exception as e:
        print(f"\n[IP-ROTATION ERROR] Could not toggle WARP: {e}. Sleeping 15s instead to cool down.\n")
        time.sleep(15)
    finally:
        error_count = 0

def get_cookies():
    try:
        cj = browser_cookie3.firefox(domain_name='cricketarchive.com')
        return {c.name: c.value for c in cj}
    except Exception as e:
        return {}

def ensure_tables(cursor):
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS ScrapedInnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT, match_id INTEGER,
            innings_number INTEGER, team_name TEXT, extras_detail TEXT,
            extras_total INTEGER, total_runs INTEGER, wickets INTEGER, overs TEXT
        );
        CREATE TABLE IF NOT EXISTS ScrapedFOW (
            id INTEGER PRIMARY KEY AUTOINCREMENT, match_id INTEGER,
            innings_number INTEGER, fow_string TEXT
        );
        CREATE TABLE IF NOT EXISTS ScrapedBatting (
            id INTEGER PRIMARY KEY AUTOINCREMENT, match_id INTEGER,
            innings_number INTEGER, player_name TEXT, dismissal TEXT,
            runs INTEGER, balls TEXT, mins TEXT, fours TEXT, sixes TEXT
        );
        CREATE TABLE IF NOT EXISTS ScrapedBowling (
            id INTEGER PRIMARY KEY AUTOINCREMENT, match_id INTEGER,
            innings_number INTEGER, player_name TEXT, overs TEXT,
            maidens TEXT, runs INTEGER, wickets INTEGER, wides TEXT, no_balls TEXT
        );
        CREATE TABLE IF NOT EXISTS ExtractorProgress (
            match_id INTEGER PRIMARY KEY
        );
    ''')

def process_match(match_id, cookies):
    global error_count
    
    # If a rotation is in progress, block this thread
    if ip_rotation_lock.locked():
        with ip_rotation_lock:
            pass # Just wait until lock is released
            
    url = f"https://cricketarchive.com/Archive/Scorecards/{match_id // 1000}/{match_id}.html"
    try:
        r = requests.get(url, impersonate="chrome110", cookies=cookies, timeout=15)
        
        if r.status_code == 403 or r.status_code == 429:
            error_count += 1
            if error_count > 5: # If multiple threads hit 403, trigger rotation
                if ip_rotation_lock.acquire(blocking=False):
                    try:
                        toggle_cloudflare()
                    finally:
                        ip_rotation_lock.release()
            return match_id, None, None, None, None, f"HTTP {r.status_code} (Re-queued)"
            
        if r.status_code != 200:
            return match_id, None, None, None, None, f"HTTP {r.status_code}"
            
        soup = BeautifulSoup(r.text, "lxml")
        tables = soup.find_all("table")
        
        innings_records = []
        fow_records = []
        batting_records = []
        bowling_records = []
        
        innings_count = 0
        bowling_innings_count = 0
        
        for table in tables:
            rows = table.find_all("tr")
            if not rows: continue
            
            first_row_text = rows[0].get_text(strip=True).lower()
            
            # Batting Table
            if "runs" in first_row_text and "mins" in first_row_text and "balls" in first_row_text:
                innings_count += 1
                
                team_name_raw = rows[0].find_all(["th", "td"])[0].get_text(strip=True)
                team_name = re.sub(r'(?i)innings', '', team_name_raw).strip()
                
                extras_detail = ""
                extras_total = 0
                total_detail = ""
                total_runs = 0
                wickets = 10
                overs = ""
                fow_string = ""
                
                for row in rows[1:]:
                    cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                    if not cells: continue
                    
                    c0 = cells[0].lower()
                    if c0 == 'extras':
                        extras_detail = cells[1] if len(cells) > 1 else ""
                        try: extras_total = int(cells[2]) if len(cells) > 2 else 0
                        except: extras_total = 0
                    elif c0 == 'total':
                        total_detail = cells[1] if len(cells) > 1 else ""
                        try: total_runs = int(cells[2]) if len(cells) > 2 else 0
                        except: total_runs = 0
                        
                        w_match = re.search(r'(\d+) wickets?', total_detail)
                        if w_match: wickets = int(w_match.group(1))
                        elif 'all out' in total_detail: wickets = 10
                        
                        o_match = re.search(r'([\d\.]+) overs?', total_detail)
                        if o_match: overs = o_match.group(1)
                    elif c0 == 'fall of wickets:':
                        pass
                    elif '-' in c0 and '(' in c0 and ')' in c0 and c0[0].isdigit():
                        fow_string = " ".join(cells)
                    elif cells[0] and c0 not in ["extras", "total", "fall of wickets:"]:
                        player = cells[0]
                        dismissal = cells[1] if len(cells) > 1 else ""
                        if dismissal.lower() == 'did not bat':
                            runs_int = 0
                            balls, mins, fours, sixes = "", "", "", ""
                        else:
                            try: runs_int = int(cells[2]) if len(cells) > 2 else 0
                            except: runs_int = 0
                            balls = cells[3] if len(cells) > 3 else "0"
                            mins = cells[4] if len(cells) > 4 else "0"
                            fours = cells[5] if len(cells) > 5 else "0"
                            sixes = cells[6] if len(cells) > 6 else "0"
                            
                        batting_records.append((match_id, innings_count, player, dismissal, runs_int, balls, mins, fours, sixes))
                        
                innings_records.append((match_id, innings_count, team_name, extras_detail, extras_total, total_runs, wickets, overs))
                if fow_string:
                    fow_records.append((match_id, innings_count, fow_string))
                        
            # Bowling Table
            elif "overs" in first_row_text and "maidens" in first_row_text and "wickets" in first_row_text:
                bowling_innings_count += 1
                for row in rows[1:]:
                    cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                    if len(cells) >= 5 and cells[0]:
                        player = cells[0]
                        overs = cells[1] if len(cells) > 1 else "0"
                        maidens = cells[2] if len(cells) > 2 else "0"
                        try: runs_int = int(cells[3]) if len(cells) > 3 else 0
                        except: runs_int = 0
                        try: wkts_int = int(cells[4]) if len(cells) > 4 else 0
                        except: wkts_int = 0
                        wides = cells[5] if len(cells) > 5 else "0"
                        no_balls = cells[6] if len(cells) > 6 else "0"
                        
                        bowling_records.append((match_id, bowling_innings_count, player, overs, maidens, runs_int, wkts_int, wides, no_balls))
                        
        return match_id, innings_records, fow_records, batting_records, bowling_records, "200"
        
    except Exception as e:
        return match_id, None, None, None, None, str(e)

def db_writer_thread(q, stop_event):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cursor = conn.cursor()
    batch = []
    
    while not stop_event.is_set() or not q.empty():
        try:
            item = q.get(timeout=1)
            batch.append(item)
            
            if len(batch) >= 100:
                all_innings = [i for b in batch for i in b[0]]
                all_fow = [i for b in batch for i in b[1]]
                all_batting = [i for b in batch for i in b[2]]
                all_bowling = [i for b in batch for i in b[3]]
                extracted_ids = [(b[4],) for b in batch]
                
                if all_innings: cursor.executemany("INSERT INTO ScrapedInnings (match_id, innings_number, team_name, extras_detail, extras_total, total_runs, wickets, overs) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", all_innings)
                if all_fow: cursor.executemany("INSERT INTO ScrapedFOW (match_id, innings_number, fow_string) VALUES (?, ?, ?)", all_fow)
                if all_batting: cursor.executemany("INSERT INTO ScrapedBatting (match_id, innings_number, player_name, dismissal, runs, balls, mins, fours, sixes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", all_batting)
                if all_bowling: cursor.executemany("INSERT INTO ScrapedBowling (match_id, innings_number, player_name, overs, maidens, runs, wickets, wides, no_balls) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", all_bowling)
                if extracted_ids: cursor.executemany("INSERT INTO ExtractorProgress (match_id) VALUES (?)", extracted_ids)
                
                conn.commit()
                batch.clear()
        except queue.Empty:
            continue
            
    # Flush remaining
    if batch:
        all_innings = [i for b in batch for i in b[0]]
        all_fow = [i for b in batch for i in b[1]]
        all_batting = [i for b in batch for i in b[2]]
        all_bowling = [i for b in batch for i in b[3]]
        extracted_ids = [(b[4],) for b in batch]
        
        if all_innings: cursor.executemany("INSERT INTO ScrapedInnings (match_id, innings_number, team_name, extras_detail, extras_total, total_runs, wickets, overs) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", all_innings)
        if all_fow: cursor.executemany("INSERT INTO ScrapedFOW (match_id, innings_number, fow_string) VALUES (?, ?, ?)", all_fow)
        if all_batting: cursor.executemany("INSERT INTO ScrapedBatting (match_id, innings_number, player_name, dismissal, runs, balls, mins, fours, sixes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", all_batting)
        if all_bowling: cursor.executemany("INSERT INTO ScrapedBowling (match_id, innings_number, player_name, overs, maidens, runs, wickets, wides, no_balls) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", all_bowling)
        if extracted_ids: cursor.executemany("INSERT INTO ExtractorProgress (match_id) VALUES (?)", extracted_ids)
        conn.commit()
    conn.close()

def main():
    print("Starting High-Speed IP-Rotating Scorecard Extractor...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    ensure_tables(cursor)
    
    cursor.execute("""
        SELECT match_id FROM ScrapedMatches 
        WHERE match_id NOT IN (SELECT match_id FROM ExtractorProgress)
        ORDER BY match_id DESC
    """)
    pending_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    print(f"Extracting mass batch of {len(pending_ids)} matches...")
    
    cookies = get_cookies()
    db_queue = queue.Queue()
    stop_event = threading.Event()
    
    # Start DB Writer thread
    writer_thread = threading.Thread(target=db_writer_thread, args=(db_queue, stop_event))
    writer_thread.start()
    
    total_processed = 0
    start_time = time.time()
    
    # Use higher worker count since we rotate IPs
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # We need a dynamic approach to handle retries
        futures_map = {executor.submit(process_match, m_id, cookies): m_id for m_id in pending_ids}
        
        for future in as_completed(futures_map):
            m_id, inn, fow, bat, bowl, status = future.result()
            
            if status == "200":
                db_queue.put((inn, fow, bat, bowl, m_id))
                total_processed += 1
            elif "403" in status or "429" in status or "error" in status.lower() or "timeout" in status.lower() or "connection" in status.lower() or "failed" in status.lower():
                # Retry this match id because it failed due to a transient network error (like an IP rotation)
                futures_map[executor.submit(process_match, m_id, cookies)] = m_id
            else:
                # Mark as done only for definitive non-transient HTTP errors (like 404)
                db_queue.put(([], [], [], [], m_id))
                total_processed += 1
                
            if total_processed % 100 == 0 and total_processed > 0:
                elapsed = time.time() - start_time
                rate = (total_processed / elapsed) * 3600
                print(f"Processed {total_processed} | Est. Speed: {rate:.0f} matches/hr")
                
    stop_event.set()
    writer_thread.join()
    print("Mass Extraction Complete.")

if __name__ == "__main__":
    main()
