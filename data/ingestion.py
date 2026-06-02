import os
import json
import sqlite3
import uuid
import glob

DB_PATH = "data/cricmatrix.db"
RAW_DIR = "data/raw/cricsheet"

def init_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            match_id TEXT PRIMARY KEY,
            date TEXT,
            venue TEXT,
            city TEXT,
            format TEXT,
            team1 TEXT,
            team2 TEXT,
            winner TEXT,
            win_margin_runs INTEGER,
            win_margin_wickets INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS deliveries (
            delivery_id TEXT PRIMARY KEY,
            match_id TEXT,
            innings INTEGER,
            over INTEGER,
            ball INTEGER,
            batter TEXT,
            bowler TEXT,
            non_striker TEXT,
            runs_batter INTEGER,
            runs_extras INTEGER,
            runs_total INTEGER,
            is_wicket INTEGER,
            dismissal_kind TEXT,
            player_dismissed TEXT,
            FOREIGN KEY(match_id) REFERENCES matches(match_id)
        )
    """)

def ingest_cricsheet_json(conn, file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    info = data.get("info", {})
    match_type = info.get("match_type", "Unknown")
    teams = info.get("teams", ["Unknown", "Unknown"])
    dates = info.get("dates", ["Unknown"])
    venue = info.get("venue", "Unknown")
    city = info.get("city", "Unknown")
    
    outcome = info.get("outcome", {})
    winner = outcome.get("winner", None)
    win_margin_runs = outcome.get("by", {}).get("runs", 0)
    win_margin_wickets = outcome.get("by", {}).get("wickets", 0)
    
    # Use cricsheet match code from filename as ID, or a UUID
    base_name = os.path.basename(file_path).split('.')[0]
    match_id = f"cricsheet_{base_name}"
    
    try:
        conn.execute("""
            INSERT OR IGNORE INTO matches 
            (match_id, date, venue, city, format, team1, team2, winner, win_margin_runs, win_margin_wickets)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (match_id, dates[0], venue, city, match_type, teams[0], teams[1], winner, win_margin_runs, win_margin_wickets))
    except sqlite3.Error as e:
        print(f"Error inserting match {match_id}: {e}")
        return

    # Ingest deliveries
    deliveries_to_insert = []
    innings_list = data.get("innings", [])
    
    for idx, inning in enumerate(innings_list):
        inning_number = idx + 1
        overs = inning.get("overs", [])
        for over_data in overs:
            over_idx = over_data.get("over", 0)
            balls = over_data.get("deliveries", [])
            for ball_idx, ball in enumerate(balls):
                batter = ball.get("batter", "")
                bowler = ball.get("bowler", "")
                non_striker = ball.get("non_striker", "")
                
                runs = ball.get("runs", {})
                r_bat = runs.get("batter", 0)
                r_ext = runs.get("extras", 0)
                r_tot = runs.get("total", 0)
                
                wickets = ball.get("wickets", [])
                is_wicket = 1 if len(wickets) > 0 else 0
                dismissal_kind = wickets[0].get("kind", "") if is_wicket else ""
                player_dismissed = wickets[0].get("player_out", "") if is_wicket else ""
                
                delivery_id = str(uuid.uuid4())
                
                deliveries_to_insert.append((
                    delivery_id, match_id, inning_number, over_idx, ball_idx + 1,
                    batter, bowler, non_striker, r_bat, r_ext, r_tot, is_wicket, dismissal_kind, player_dismissed
                ))
    
    try:
        conn.executemany("""
            INSERT OR IGNORE INTO deliveries
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, deliveries_to_insert)
    except sqlite3.Error as e:
        print(f"Error inserting deliveries for {match_id}: {e}")

def run_pipeline():
    print("[*] Starting CricMatrix ETL Pipeline...")
    files = glob.glob(os.path.join(RAW_DIR, "*.json"))
    if not files:
        print("[!] No JSON files found in Bronze Layer. Run the spider first.")
        return
        
    print(f"[*] Found {len(files)} files to ingest. Processing...")
    
    with sqlite3.connect(DB_PATH) as conn:
        init_db(conn)
        # Process all files
        for i, file_path in enumerate(files):
            ingest_cricsheet_json(conn, file_path)
            if i > 0 and i % 50 == 0:
                print(f"[+] Processed {i}/{len(files)} matches...")
                
        cursor = conn.execute("SELECT COUNT(*) FROM matches")
        m_count = cursor.fetchone()[0]
        cursor = conn.execute("SELECT COUNT(*) FROM deliveries")
        d_count = cursor.fetchone()[0]
        print(f"[+] ETL Complete. Database now contains {m_count} matches and {d_count} deliveries.")

if __name__ == "__main__":
    run_pipeline()
