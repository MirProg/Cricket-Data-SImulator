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
        print("\n[IP-ROTATION] Toggling Cloudflare WARP to cycle IP...")
        subprocess.run(["warp-cli", "disconnect"], check=True, capture_output=True, timeout=10)
        time.sleep(2)
        subprocess.run(["warp-cli", "connect"], check=True, capture_output=True, timeout=10)
        time.sleep(5)
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

def scrape_commentary(match_id, innings_number, cookies):
    deliveries = []
    page = 1
    while True:
        url = f"https://cricketarchive.com/Archive/Scorecards/{match_id // 1000}/{match_id}_commentary_i{innings_number}_page{page if page > 1 else ''}.html"
        try:
            r = requests.get(url, impersonate="chrome110", cookies=cookies, timeout=10)
            if r.status_code != 200:
                break
            
            soup = BeautifulSoup(r.text, 'lxml')
            tables = soup.find_all('table')
            found_deliveries = False
            for t in tables:
                rows = t.find_all('tr')
                if not rows: continue
                first_cell = rows[0].get_text(strip=True)
                if '.' in first_cell and first_cell.split('.')[0].isdigit():
                    # This is likely the commentary table
                    found_deliveries = True
                    for row in rows:
                        cells = [c.get_text(strip=True) for c in row.find_all(['td'])]
                        if len(cells) >= 3:
                            over_ball = cells[0]
                            bowler_batter = cells[1]
                            comm_text = cells[2]
                            
                            m_ob = re.search(r'(\d+)\.(\d+)', over_ball)
                            if m_ob:
                                ov = int(m_ob.group(1))
                                bl = int(m_ob.group(2))
                                ov_fmt = float(over_ball)
                            else: continue
                            
                            b_name, bat_name = "", ""
                            if ' to ' in bowler_batter:
                                parts = bowler_batter.split(' to ')
                                b_name = parts[0].strip()
                                bat_name = parts[1].strip()
                                
                            runs = 0
                            is_boundary = False
                            is_wicket = 'OUT' in comm_text or 'out' in comm_text.lower()
                            extras = 0
                            
                            if 'FOUR' in comm_text or '4 runs' in comm_text:
                                runs = 4
                                is_boundary = True
                            elif 'SIX' in comm_text or '6 runs' in comm_text:
                                runs = 6
                                is_boundary = True
                            elif 'no run' in comm_text.lower(): runs = 0
                            elif '1 run' in comm_text.lower(): runs = 1
                            elif '2 runs' in comm_text.lower(): runs = 2
                            elif '3 runs' in comm_text.lower(): runs = 3
                            
                            deliveries.append((
                                str(match_id), innings_number, ov, bl, ov_fmt, b_name, bat_name, "",
                                runs, extras, "", is_wicket, "", "", is_boundary, comm_text
                            ))
            if not found_deliveries or 'Next Page' not in r.text:
                break
            page += 1
        except:
            break
    return deliveries

def process_match(match_id, cookies):
    global error_count
    
    if ip_rotation_lock.locked():
        with ip_rotation_lock:
            pass
            
    url = f"https://cricketarchive.com/Archive/Scorecards/{match_id // 1000}/{match_id}.html"
    try:
        r = requests.get(url, impersonate="chrome110", cookies=cookies, timeout=15)
        
        if r.status_code == 403 or r.status_code == 429:
            error_count += 1
            if error_count > 5:
                if ip_rotation_lock.acquire(blocking=False):
                    try:
                        toggle_cloudflare()
                    finally:
                        ip_rotation_lock.release()
            return match_id, None, None, None, None, None, None, f"HTTP {r.status_code} (Re-queued)"
            
        if r.status_code != 200:
            return match_id, None, None, None, None, None, None, f"HTTP {r.status_code}"
            
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
        if m_venue:
            meta['venue_name'] = m_venue.group(1).strip()
            meta['match_date'] = m_venue.group(2).strip()

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

        m_ref = re.search(r'Referee\s*(.*?)\s*Scorers', full_text)
        if m_ref: meta['referee'] = m_ref.group(1).strip()
        
        for b in soup.find_all('b'):
            if b.text == 'Balls per over':
                meta['balls_per_over'] = int(b.next_sibling.strip()) if b.next_sibling else 6

        innings_records = []
        fow_records = []
        batting_records = []
        bowling_records = []
        
        innings_count = 0
        bowling_innings_count = 0
        
        tables = soup.find_all("table")
        for t in tables:
            rows = t.find_all("tr")
            if not rows: continue
            
            first_row_text = rows[0].get_text(separator=' ').lower()
            
            if "runs" in first_row_text and "mins" in first_row_text and "s-rate" in first_row_text:
                innings_count += 1
                team_name = first_row_text.split("innings")[0].strip()
                
                extras_string = ""
                total_runs = 0
                wickets = 0
                overs_str = "0"
                
                for row in rows[1:]:
                    cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                    if len(cells) >= 7 and "Extras" not in cells[0] and "Total" not in cells[0]:
                        player = cells[0]
                        dismissal = cells[1]
                        
                        is_cap = '*' in player
                        is_wk = '+' in player
                        player_clean = player.replace('*', '').replace('+', '').strip()
                        
                        sub_type = ""
                        if 'Concussion' in dismissal or 'Concussion' in player: sub_type = 'Concussion Sub'
                        elif 'Impact' in dismissal or 'Impact' in player: sub_type = 'Impact Player'
                        
                        try: r = int(cells[2])
                        except: r = 0
                        try: b = int(cells[3])
                        except: b = 0
                        try: m = int(cells[4])
                        except: m = 0
                        try: f = int(cells[5])
                        except: f = 0
                        try: s = int(cells[6])
                        except: s = 0
                        try: sr = float(cells[7])
                        except: sr = 0.0
                        
                        is_golden = (r == 0 and b == 1)
                        is_diamond = (r == 0 and b == 0 and 'run out' in dismissal.lower())
                        bound_perc = ((f*4 + s*6) / r * 100) if r > 0 else 0.0
                        
                        batting_records.append((
                            str(match_id), innings_count, len(batting_records)+1, player_clean, is_cap, is_wk, sub_type,
                            dismissal, "", "", "", r, b, m, f, s, sr, bound_perc, is_golden, is_diamond, False
                        ))
                    
                    elif len(cells) > 0 and "Extras" in cells[0]:
                        extras_string = " ".join(cells[1:])
                    elif len(cells) > 0 and "Total" in cells[0]:
                        total_str = cells[1]
                        m_tot = re.search(r'(\d+)', total_str)
                        if m_tot: total_runs = int(m_tot.group(1))
                        m_wkt = re.search(r'(\d+) wicket', total_str)
                        if m_wkt: wickets = int(m_wkt.group(1))
                        else: wickets = 10 if 'all out' in total_str else 0
                        m_ov = re.search(r'(\d+\.?\d*) over', total_str)
                        if m_ov: overs_str = m_ov.group(1)
                
                byes = leg_byes = wides = no_balls = penalties = 0
                for pt in extras_string.split(','):
                    pt = pt.strip().replace('(', '').replace(')', '')
                    m = re.search(r'([a-z\s]+)\s*(\d+)', pt)
                    if m:
                        typ = m.group(1).strip()
                        val = int(m.group(2))
                        if typ == 'b': byes = val
                        elif typ == 'lb': leg_byes = val
                        elif typ == 'w': wides = val
                        elif typ == 'nb': no_balls = val
                        elif typ == 'p': penalties = val
                
                is_chasing = (innings_count == 2 or innings_count == 4)
                
                innings_records.append((
                    str(match_id), innings_count, team_name, "", is_chasing, total_runs, wickets, float(overs_str), 
                    False, False, extras_string, byes, leg_byes, wides, no_balls, penalties
                ))

                next_div = t.find_next_sibling('div')
                if next_div and 'Fall of wickets' in next_div.text:
                    fow_text = next_div.text.replace('Fall of wickets:', '').strip()
                    prev_score = 0
                    for pt in fow_text.split(','):
                        pt = pt.strip()
                        m = re.search(r'(\d+)-(\d+)\s*\((.*?)\)', pt)
                        if m:
                            score = int(m.group(1))
                            wkt = int(m.group(2))
                            player_out = m.group(3).strip()
                            part_runs = score - prev_score
                            prev_score = score
                            fow_records.append((str(match_id), innings_count, wkt, score, part_runs, player_out, 0.0))
            
            elif "overs" in first_row_text and "mdns" in first_row_text and "wkts" in first_row_text:
                bowling_innings_count += 1
                for row in rows[1:]:
                    cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                    if len(cells) >= 11 and cells[0]:
                        player = cells[0].replace('*', '').replace('+', '').strip()
                        try: o = float(cells[1])
                        except: o = 0.0
                        try: md = int(cells[2])
                        except: md = 0
                        try: r = int(cells[3])
                        except: r = 0
                        try: w = int(cells[4])
                        except: w = 0
                        try: wd = int(cells[5])
                        except: wd = 0
                        try: nb = int(cells[6])
                        except: nb = 0
                        try: dots = int(cells[7])
                        except: dots = 0
                        try: econ = float(cells[10])
                        except: econ = 0.0
                        
                        bowling_records.append((str(match_id), bowling_innings_count, len(bowling_records)+1, player, False, o, md, r, w, wd, nb, dots, econ))

        all_deliveries = []
        if 'Ball-by-ball' in r.text:
            for i in range(1, innings_count + 1):
                dels = scrape_commentary(match_id, i, cookies)
                all_deliveries.extend(dels)

        return match_id, innings_records, fow_records, batting_records, bowling_records, all_deliveries, meta, "200"
        
    except Exception as e:
        return match_id, None, None, None, None, None, None, str(e)

def db_writer_thread(q, stop_event):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cursor = conn.cursor()
    batch = []
    
    while not stop_event.is_set() or not q.empty():
        try:
            item = q.get(timeout=1)
            batch.append(item)
            
            if len(batch) >= 20:
                all_innings = [i for b in batch for i in b[0] if b[0]]
                all_fow = [i for b in batch for i in b[1] if b[1]]
                all_batting = [i for b in batch for i in b[2] if b[2]]
                all_bowling = [i for b in batch for i in b[3] if b[3]]
                all_deliveries = [i for b in batch for i in b[4] if b[4]]
                extracted_ids = [(str(b[5]),) for b in batch]
                
                all_meta = []
                for b in batch:
                    if b[6]:
                        m = b[6]
                        all_meta.append((
                            str(b[5]), "", m['teams'], m['home_team'], m['away_team'], m['series'],
                            m['match_date'], "", "", m['venue_name'], m['match_type'], m['day_night'],
                            m['balls_per_over'], m['toss_winner'], m['toss_decision'], m['result_string'],
                            m['winning_team'], m['win_margin'], m['is_dls_used'], m['has_super_over'],
                            m['follow_on_enforced'], m['points'], m['umpires'], m['referee'],
                            m['player_of_match'], m['player_of_series'], m['match_notes']
                        ))
                
                if all_meta: cursor.executemany("INSERT OR REPLACE INTO ScrapedMatches (id, url, teams, home_team, away_team, series, match_date, season, venue_id, venue_name, match_type, day_night, balls_per_over, toss_winner, toss_decision, result_string, winning_team, win_margin, is_dls_used, has_super_over, follow_on_enforced, points, umpires, referee, player_of_match, player_of_series, match_notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", all_meta)
                if all_innings: cursor.executemany("INSERT INTO ScrapedInnings (match_id, innings_number, batting_team, bowling_team, is_chasing, total_runs, wickets, overs, is_declared, is_forfeited, extras_string, extras_byes, extras_leg_byes, extras_wides, extras_no_balls, extras_penalties_awarded) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", all_innings)
                if all_batting: cursor.executemany("INSERT INTO ScrapedBatting (match_id, innings_number, batting_position, player_name, is_captain, is_wicketkeeper, substitute_type, dismissal_string, dismissal_type, dismissal_bowler, dismissal_fielder, runs, balls, minutes_batted, fours, sixes, strike_rate, boundary_percentage, is_golden_duck, is_diamond_duck, is_finisher_knock) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", all_batting)
                if all_bowling: cursor.executemany("INSERT INTO ScrapedBowling (match_id, innings_number, bowling_position, player_name, is_substitute, overs, maidens, runs_conceded, wickets, wides, no_balls, dots, economy) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", all_bowling)
                if all_fow: cursor.executemany("INSERT INTO ScrapedFOW (match_id, innings_number, wicket_number, team_score, partnership_runs, player_out, overs) VALUES (?, ?, ?, ?, ?, ?, ?)", all_fow)
                if all_deliveries: cursor.executemany("INSERT INTO ScrapedDeliveries (match_id, innings_number, over_number, ball_number, overs_formatted, bowler_name, batter_name, non_striker_name, runs_batter, extras, extras_type, is_wicket, wicket_type, player_out, is_boundary, commentary_text) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", all_deliveries)
                if extracted_ids: cursor.executemany("INSERT OR REPLACE INTO ExtractorProgress (match_id, status) VALUES (?, 'DONE')", extracted_ids)
                
                conn.commit()
                batch.clear()
        except queue.Empty:
            continue
            
    # Flush remaining
    if batch:
        all_innings = [i for b in batch for i in b[0] if b[0]]
        all_fow = [i for b in batch for i in b[1] if b[1]]
        all_batting = [i for b in batch for i in b[2] if b[2]]
        all_bowling = [i for b in batch for i in b[3] if b[3]]
        all_deliveries = [i for b in batch for i in b[4] if b[4]]
        extracted_ids = [(str(b[5]),) for b in batch]
        
        all_meta = []
        for b in batch:
            if b[6]:
                m = b[6]
                all_meta.append((
                    str(b[5]), "", m['teams'], m['home_team'], m['away_team'], m['series'],
                    m['match_date'], "", "", m['venue_name'], m['match_type'], m['day_night'],
                    m['balls_per_over'], m['toss_winner'], m['toss_decision'], m['result_string'],
                    m['winning_team'], m['win_margin'], m['is_dls_used'], m['has_super_over'],
                    m['follow_on_enforced'], m['points'], m['umpires'], m['referee'],
                    m['player_of_match'], m['player_of_series'], m['match_notes']
                ))
        
        if all_meta: cursor.executemany("INSERT OR REPLACE INTO ScrapedMatches (id, url, teams, home_team, away_team, series, match_date, season, venue_id, venue_name, match_type, day_night, balls_per_over, toss_winner, toss_decision, result_string, winning_team, win_margin, is_dls_used, has_super_over, follow_on_enforced, points, umpires, referee, player_of_match, player_of_series, match_notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", all_meta)
        if all_innings: cursor.executemany("INSERT INTO ScrapedInnings (match_id, innings_number, batting_team, bowling_team, is_chasing, total_runs, wickets, overs, is_declared, is_forfeited, extras_string, extras_byes, extras_leg_byes, extras_wides, extras_no_balls, extras_penalties_awarded) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", all_innings)
        if all_batting: cursor.executemany("INSERT INTO ScrapedBatting (match_id, innings_number, batting_position, player_name, is_captain, is_wicketkeeper, substitute_type, dismissal_string, dismissal_type, dismissal_bowler, dismissal_fielder, runs, balls, minutes_batted, fours, sixes, strike_rate, boundary_percentage, is_golden_duck, is_diamond_duck, is_finisher_knock) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", all_batting)
        if all_bowling: cursor.executemany("INSERT INTO ScrapedBowling (match_id, innings_number, bowling_position, player_name, is_substitute, overs, maidens, runs_conceded, wickets, wides, no_balls, dots, economy) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", all_bowling)
        if all_fow: cursor.executemany("INSERT INTO ScrapedFOW (match_id, innings_number, wicket_number, team_score, partnership_runs, player_out, overs) VALUES (?, ?, ?, ?, ?, ?, ?)", all_fow)
        if all_deliveries: cursor.executemany("INSERT INTO ScrapedDeliveries (match_id, innings_number, over_number, ball_number, overs_formatted, bowler_name, batter_name, non_striker_name, runs_batter, extras, extras_type, is_wicket, wicket_type, player_out, is_boundary, commentary_text) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", all_deliveries)
        if extracted_ids: cursor.executemany("INSERT OR REPLACE INTO ExtractorProgress (match_id, status) VALUES (?, 'DONE')", extracted_ids)
        
        conn.commit()
    conn.close()

def main():
    print("Starting V2 Advanced Analytics Scorecard Extractor...")
    # Because we dropped the original ScrapedMatches to rebuild the schema, we need to generate match IDs.
    # CricketArchive match IDs go up to roughly 1,450,000. For this run, we will scan the most recent 100,000.
    start_id = 1420000
    end_id = 1430000
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT match_id FROM ExtractorProgress WHERE status='DONE'")
    done_ids = {int(row[0]) for row in cursor.fetchall()}
    conn.close()
    
    pending_ids = [m_id for m_id in range(end_id, start_id, -1) if m_id not in done_ids]
    print(f"Queueing {len(pending_ids)} recent matches for deep extraction...")
    
    cookies = get_cookies()
    db_queue = queue.Queue()
    stop_event = threading.Event()
    
    writer_thread = threading.Thread(target=db_writer_thread, args=(db_queue, stop_event))
    writer_thread.start()
    
    total_processed = 0
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures_map = {executor.submit(process_match, m_id, cookies): m_id for m_id in pending_ids}
        
        for future in as_completed(futures_map):
            m_id, inn, fow, bat, bowl, dels, meta, status = future.result()
            
            if status == "200":
                db_queue.put((inn, fow, bat, bowl, dels, m_id, meta))
                total_processed += 1
            elif "403" in status or "429" in status or "error" in status.lower() or "timeout" in status.lower() or "connection" in status.lower() or "failed" in status.lower():
                futures_map[executor.submit(process_match, m_id, cookies)] = m_id
            else:
                db_queue.put(([], [], [], [], [], m_id, None))
                total_processed += 1
                
            if total_processed % 10 == 0 and total_processed > 0:
                elapsed = time.time() - start_time
                rate = (total_processed / elapsed) * 3600
                print(f"Processed {total_processed} | Est. Speed: {rate:.0f} matches/hr")
                
    stop_event.set()
    writer_thread.join()
    print("V2 Mass Extraction Complete.")

if __name__ == "__main__":
    main()
