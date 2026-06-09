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
MAX_WORKERS = 30

ip_rotation_lock = threading.Lock()
error_count = 0

def toggle_cloudflare():
    global error_count
    try:
        subprocess.run(["warp-cli", "disconnect"], check=True, capture_output=True, timeout=10)
        time.sleep(2)
        subprocess.run(["warp-cli", "connect"], check=True, capture_output=True, timeout=10)
        time.sleep(5)
    except Exception as e:
        print("Failed to toggle warp-cli:", e)
        time.sleep(15)
    finally:
        error_count = 0

def get_cookies():
    try:
        cj = browser_cookie3.firefox(domain_name='cricketarchive.com')
        return {c.name: c.value for c in cj}
    except Exception as e:
        return {}

def scrape_commentary(match_id, innings_number, cookies):
    deliveries = []
    page = 1
    while True:
        url = f"https://cricketarchive.com/Archive/Scorecards/{match_id // 1000}/{match_id}_commentary_i{innings_number}_page{page if page > 1 else ''}.html"
        try:
            r = requests.get(url, impersonate="chrome110", cookies=cookies, timeout=10)
            if r.status_code != 200: break
            soup = BeautifulSoup(r.text, 'lxml')
            tables = soup.find_all('table')
            found_deliveries = False
            for t in tables:
                rows = t.find_all('tr')
                if not rows: continue
                first_cell = rows[0].get_text(strip=True)
                if '.' in first_cell and first_cell.split('.')[0].isdigit():
                    found_deliveries = True
                    for row in rows:
                        cells = [c.get_text(strip=True) for c in row.find_all(['td'])]
                        if len(cells) >= 3:
                            over_ball, bowler_batter, comm_text = cells[0], cells[1], cells[2]
                            m_ob = re.search(r'(\d+)\.(\d+)', over_ball)
                            if not m_ob: continue
                            ov, bl = int(m_ob.group(1)), int(m_ob.group(2))
                            b_name, bat_name = "", ""
                            if ' to ' in bowler_batter:
                                parts = bowler_batter.split(' to ')
                                b_name, bat_name = parts[0].strip(), parts[1].strip()
                            
                            runs, is_boundary = 0, False
                            is_wicket = 'OUT' in comm_text or 'out' in comm_text.lower()
                            if 'FOUR' in comm_text or '4 runs' in comm_text: runs, is_boundary = 4, True
                            elif 'SIX' in comm_text or '6 runs' in comm_text: runs, is_boundary = 6, True
                            elif '1 run' in comm_text.lower(): runs = 1
                            elif '2 runs' in comm_text.lower(): runs = 2
                            elif '3 runs' in comm_text.lower(): runs = 3
                            
                            deliveries.append((str(match_id), innings_number, ov, bl, float(over_ball), b_name, bat_name, "", runs, 0, "", is_wicket, "", "", is_boundary, comm_text))
            if not found_deliveries or 'Next Page' not in r.text: break
            page += 1
        except: break
    return deliveries

def process_match(match_id, cookies):
    global error_count
    if ip_rotation_lock.locked():
        with ip_rotation_lock: pass
            
    url = f"https://cricketarchive.com/Archive/Scorecards/{match_id // 1000}/{match_id}.html"
    try:
        r = requests.get(url, impersonate="chrome110", cookies=cookies, timeout=15)
        if r.status_code == 403 or r.status_code == 429:
            error_count += 1
            if error_count > 5 and ip_rotation_lock.acquire(blocking=False):
                try:
                    print("\n[IP-ROTATION] Toggling Cloudflare WARP to cycle IP...")
                    toggle_cloudflare()
                    print("[IP-ROTATION] IP Cycled successfully.\n")
                finally: ip_rotation_lock.release()
            return match_id, None, None, None, None, None, None, f"HTTP {r.status_code} (Re-queued)"
        if r.status_code != 200: return match_id, None, None, None, None, None, None, f"HTTP {r.status_code}"
            
        soup = BeautifulSoup(r.text, "lxml")
        full_text = soup.get_text(separator=' ')
        
        meta = {
            'teams': "", 'home_team': "", 'away_team': "", 'series': "", 'venue_name': "", 'match_date': "", 
            'match_type': "", 'day_night': False, 'balls_per_over': 6, 
            'toss_winner': "", 'toss_decision': "", 'result_string': "", 'winning_team': "", 'win_margin': "",
            'is_dls_used': False, 'has_super_over': False, 'follow_on_enforced': False,
            'points': "", 'umpires': "", 'referee': "", 'player_of_match': "", 'player_of_series': "", 'match_notes': ""
        }
        
        m_teams = re.search(r'([A-Za-z\s]+ v [A-Za-z\s]+)', full_text)
        if m_teams: meta['teams'] = m_teams.group(1).strip()
        m_venue = re.search(r'Venue\s*(.*?)\s*on\s*(\d+[a-z]{2}\s+[A-Za-z]+\s+\d{4})', full_text)
        if m_venue: meta['venue_name'], meta['match_date'] = m_venue.group(1).strip(), m_venue.group(2).strip()
        m_type = re.search(r'\(([\w\-\s]+match.*?)\)', full_text)
        if m_type: meta['match_type'] = m_type.group(1).strip()
        if 'day/night' in full_text.lower(): meta['day_night'] = True
        m_toss = re.search(r'Toss\s*(.*?)\s*Result', full_text)
        if m_toss: meta['toss_winner'] = m_toss.group(1).strip()
        m_res = re.search(r'Result\s*(.*?)\s*Points', full_text)
        if m_res: meta['result_string'] = m_res.group(1).strip()
        if 'Super Over' in full_text or 'eliminator' in full_text.lower(): meta['has_super_over'] = True
        if 'D/L method' in full_text or 'DLS method' in full_text: meta['is_dls_used'] = True
        if 'follow-on' in full_text.lower(): meta['follow_on_enforced'] = True
        m_pts = re.search(r'Points\s*(.*?)\s*Umpires', full_text)
        if m_pts: meta['points'] = m_pts.group(1).strip()
        m_ump = re.search(r'Umpires\s*(.*?)\s*Referee', full_text)
        if m_ump: meta['umpires'] = m_ump.group(1).strip()
        
        for b in soup.find_all('b'):
            if b.text == 'Balls per over': meta['balls_per_over'] = int(b.next_sibling.strip()) if b.next_sibling else 6

        innings_records, fow_records, batting_records, bowling_records = [], [], [], []
        innings_count = bowling_innings_count = 0
        
        for t in soup.find_all("table"):
            rows = t.find_all("tr")
            if not rows: continue
            
            header_cells = [c.get_text(strip=True).lower() for c in rows[0].find_all(['th', 'td'])]
            header_text = " ".join(header_cells)
            
            if "innings" in header_text and "runs" in header_text and "bowling" not in header_text:
                innings_count += 1
                team_name = header_text.split("innings")[0].strip()
                
                idx_r = header_cells.index("runs") if "runs" in header_cells else -1
                idx_b = header_cells.index("balls") if "balls" in header_cells else -1
                idx_m = header_cells.index("mins") if "mins" in header_cells else -1
                idx_4s = header_cells.index("4s") if "4s" in header_cells else -1
                idx_6s = header_cells.index("6s") if "6s" in header_cells else -1
                idx_sr = header_cells.index("s-rate") if "s-rate" in header_cells else -1
                
                extras_string, total_runs, wickets, overs_str = "", 0, 0, "0"
                
                for row in rows[1:]:
                    cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                    if len(cells) >= 3 and "Extras" not in cells[0] and "Total" not in cells[0]:
                        player = cells[0]
                        dismissal = cells[1] if len(cells) > 1 else ""
                        is_cap, is_wk = '*' in player, '+' in player
                        player_clean = player.replace('*', '').replace('+', '').strip()
                        sub_type = 'Concussion Sub' if 'Concussion' in dismissal else 'Impact Player' if 'Impact' in dismissal else ""
                        
                        r = int(cells[idx_r]) if idx_r != -1 and idx_r < len(cells) and cells[idx_r].isdigit() else 0
                        b = int(cells[idx_b]) if idx_b != -1 and idx_b < len(cells) and cells[idx_b].isdigit() else 0
                        m = int(cells[idx_m]) if idx_m != -1 and idx_m < len(cells) and cells[idx_m].isdigit() else 0
                        f = int(cells[idx_4s]) if idx_4s != -1 and idx_4s < len(cells) and cells[idx_4s].isdigit() else 0
                        s = int(cells[idx_6s]) if idx_6s != -1 and idx_6s < len(cells) and cells[idx_6s].isdigit() else 0
                        try: sr = float(cells[idx_sr]) if idx_sr != -1 and idx_sr < len(cells) else 0.0
                        except: sr = 0.0
                        
                        batting_records.append((str(match_id), innings_count, len(batting_records)+1, player_clean, is_cap, is_wk, sub_type, dismissal, "", "", "", r, b, m, f, s, sr, 0.0, False, False, False))
                    elif len(cells) > 0 and "Extras" in cells[0]: extras_string = " ".join(cells[1:])
                    elif len(cells) > 0 and "Total" in cells[0]:
                        total_str = cells[1] if len(cells) > 1 else ""
                        m_tot = re.search(r'(\d+)', total_str)
                        if m_tot: total_runs = int(m_tot.group(1))
                        m_wkt = re.search(r'(\d+) wicket', total_str)
                        if m_wkt: wickets = int(m_wkt.group(1))
                        else: wickets = 10 if 'all out' in total_str else 0
                        m_ov = re.search(r'(\d+\.?\d*) over', total_str)
                        if m_ov: overs_str = m_ov.group(1)
                
                innings_records.append((str(match_id), innings_count, team_name, "", False, total_runs, wickets, float(overs_str), False, False, extras_string, 0, 0, 0, 0, 0))
            
            elif "bowling" in header_text and "overs" in header_text and "runs" in header_text:
                bowling_innings_count += 1
                idx_o = header_cells.index("overs") if "overs" in header_cells else -1
                idx_md = header_cells.index("mdns") if "mdns" in header_cells else -1
                idx_r = header_cells.index("runs") if "runs" in header_cells else -1
                idx_w = header_cells.index("wkts") if "wkts" in header_cells else -1
                idx_wd = header_cells.index("wides") if "wides" in header_cells else -1
                idx_nb = header_cells.index("no-balls") if "no-balls" in header_cells else -1
                
                for row in rows[1:]:
                    cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                    if len(cells) >= 3 and cells[0]:
                        player = cells[0].replace('*', '').replace('+', '').strip()
                        try: o = float(cells[idx_o]) if idx_o != -1 and idx_o < len(cells) else 0.0
                        except: o = 0.0
                        r = int(cells[idx_r]) if idx_r != -1 and idx_r < len(cells) and cells[idx_r].isdigit() else 0
                        w = int(cells[idx_w]) if idx_w != -1 and idx_w < len(cells) and cells[idx_w].isdigit() else 0
                        bowling_records.append((str(match_id), bowling_innings_count, len(bowling_records)+1, player, False, o, 0, r, w, 0, 0, 0, 0.0))

        all_deliveries = []
        if 'Ball-by-ball' in r.text:
            for i in range(1, innings_count + 1):
                all_deliveries.extend(scrape_commentary(match_id, i, cookies))

        return match_id, innings_records, fow_records, batting_records, bowling_records, all_deliveries, meta, "200"
        
    except Exception as e:
        return match_id, None, None, None, None, None, None, str(e)

def db_writer_thread(q, stop_event):
    conn = sqlite3.connect(DB_PATH, timeout=60)
    cursor = conn.cursor()
    batch = []
    
    while not stop_event.is_set() or not q.empty():
        try:
            item = q.get(timeout=1)
            batch.append(item)
            if len(batch) >= 20 or (stop_event.is_set() and q.empty()):
                all_meta, all_innings, all_batting, all_bowling, all_fow, all_deliveries = [], [], [], [], [], []
                for m_id, i_rec, f_rec, b_rec, bw_rec, d_rec, m_data, status in batch:
                    if status == "200" and m_data:
                        all_meta.append((m_id, m_data['teams'], m_data['home_team'], m_data['away_team'], m_data['series'], m_data['venue_name'], m_data['match_date'], m_data['match_type'], m_data['day_night'], m_data['balls_per_over'], m_data['toss_winner'], m_data['toss_decision'], m_data['result_string'], m_data['winning_team'], m_data['win_margin'], m_data['is_dls_used'], m_data['has_super_over'], m_data['follow_on_enforced'], m_data['points'], m_data['umpires'], m_data['referee'], m_data['player_of_match'], m_data['player_of_series'], m_data['match_notes']))
                        if i_rec: all_innings.extend(i_rec)
                        if b_rec: all_batting.extend(b_rec)
                        if bw_rec: all_bowling.extend(bw_rec)
                        if d_rec: all_deliveries.extend(d_rec)
                
                try:
                    if all_meta: cursor.executemany("INSERT OR REPLACE INTO ScrapedMatches (id, teams, home_team, away_team, series, venue_name, match_date, match_type, day_night, balls_per_over, toss_winner, toss_decision, result_string, winning_team, win_margin, is_dls_used, has_super_over, follow_on_enforced, points, umpires, referee, player_of_match, player_of_series, match_notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", all_meta)
                    if all_innings: cursor.executemany("INSERT INTO ScrapedInnings (match_id, innings_number, team_name, opponent_team, is_declared, total_runs, total_wickets, total_overs, is_follow_on, is_forfeited, extras_string, byes, leg_byes, wides, no_balls, penalty_runs) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", all_innings)
                    if all_batting: cursor.executemany("INSERT INTO ScrapedBatting (match_id, innings_number, batting_position, player_name, is_captain, is_wicketkeeper, substitute_type, dismissal_string, dismissal_type, dismissal_bowler, dismissal_fielder, runs, balls, minutes_batted, fours, sixes, strike_rate, boundary_percentage, is_golden_duck, is_diamond_duck, is_finisher_knock) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", all_batting)
                    if all_bowling: cursor.executemany("INSERT INTO ScrapedBowling (match_id, innings_number, bowling_position, player_name, is_captain, overs, maidens, runs, wickets, wides, no_balls, dot_balls, economy_rate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", all_bowling)
                    if all_deliveries: cursor.executemany("INSERT INTO ScrapedDeliveries (match_id, innings_number, over_number, ball_number, over_ball, bowler_name, batter_name, non_striker_name, runs_batter, runs_extras, extra_type, is_wicket, dismissal_type, dismissal_player, is_boundary, commentary_text) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", all_deliveries)
                    conn.commit()
                except Exception as e:
                    print("DB Insert Error:", e)
                    conn.rollback()
                batch.clear()
        except queue.Empty: continue
        except Exception as e:
            print("DB Writer fatal crash:", e)
            break
    conn.close()

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS ExtractedProgress (match_id TEXT PRIMARY KEY)")
    done = {r[0] for r in c.execute("SELECT match_id FROM ExtractedProgress").fetchall()}
    conn.close()
    
    start_id = 1430000
    end_id = 1420000
    pending_ids = [i for i in range(start_id, end_id, -1) if str(i) not in done]
    
    cookies = get_cookies()
    q = queue.Queue()
    stop_event = threading.Event()
    writer = threading.Thread(target=db_writer_thread, args=(q, stop_event))
    writer.start()
    
    total_processed = 0
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_match, m_id, cookies): m_id for m_id in pending_ids}
        for future in as_completed(futures):
            res = future.result()
            m_id = res[0]
            status = res[7]
            if status == "200":
                q.put(res)
                conn = sqlite3.connect(DB_PATH, timeout=60)
                conn.execute("INSERT OR IGNORE INTO ExtractedProgress (match_id) VALUES (?)", (str(m_id),))
                conn.commit()
                conn.close()
            elif "HTTP 404" in status:
                conn = sqlite3.connect(DB_PATH, timeout=60)
                conn.execute("INSERT OR IGNORE INTO ExtractedProgress (match_id) VALUES (?)", (str(m_id),))
                conn.commit()
                conn.close()
            elif "Re-queued" in status:
                futures[executor.submit(process_match, m_id, cookies)] = m_id
                
            total_processed += 1
            if total_processed % 10 == 0:
                elapsed = time.time() - start_time
                speed = (total_processed / elapsed) * 3600
                print(f"Processed {total_processed} | Est. Speed: {int(speed)} matches/hr")
                
    stop_event.set()
    writer.join()
    print("V2 Mass Extraction Complete.")

if __name__ == "__main__":
    main()
