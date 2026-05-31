import sqlite3
import random
from datetime import datetime, timedelta

def generate_massive_data():
    conn = sqlite3.connect('data/cricket_db.sqlite')
    cursor = conn.cursor()

    # Expand Schema to include Series and Leagues
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS Series (
            series_id TEXT PRIMARY KEY,
            name TEXT,
            start_date TEXT,
            end_date TEXT,
            type TEXT
        );
        CREATE TABLE IF NOT EXISTS Leagues (
            league_id TEXT PRIMARY KEY,
            name TEXT,
            country TEXT,
            status TEXT
        );
        -- Alter Matches to link to Series/League if needed, though we can just map by date for now.
    """)

    # 1. Leagues
    leagues = [
        ("ipl", "Indian Premier League 2026", "India", "Completed"),
        ("psl", "Pakistan Super League 2026", "Pakistan", "Completed"),
        ("t20-blast", "T20 Blast 2026", "England", "In Progress"),
        ("bbl", "Big Bash League", "Australia", "Completed"),
        ("cpl", "Caribbean Premier League", "West Indies", "Upcoming")
    ]
    cursor.executemany("INSERT OR REPLACE INTO Leagues VALUES (?, ?, ?, ?)", leagues)

    # 2. Series
    series_data = [
        ("asian-games", "Asian Games Qualifier 2026", "2026-05-01", "2026-05-15", "International"),
        ("aus-pak", "Australia tour of Pakistan 2026", "2026-05-30", "2026-06-15", "International"),
        ("nz-ire", "New Zealand tour of Ireland 2026", "2026-05-27", "2026-06-10", "International"),
        ("t20-wc", "ICC Men's T20 World Cup 2026", "2026-02-07", "2026-03-08", "Tournament")
    ]
    cursor.executemany("INSERT OR REPLACE INTO Series VALUES (?, ?, ?, ?, ?)", series_data)

    # 3. Massive Matches & Stats Generation
    teams = ["India", "Australia", "England", "Pakistan", "South Africa", "New Zealand", "Sri Lanka", "West Indies"]
    formats = ["T20I", "ODI", "Test"]
    venues = ["Lord's", "MCG", "Wankhede", "Eden Gardens", "Gaddafi Stadium", "SCG", "Newlands"]

    base_date = datetime.now()
    matches = []
    player_match_stats = []
    
    # Generate 5,000 matches going back 10 years
    for i in range(5000):
        match_id = f"ARCHIVE_M_{i}"
        t1, t2 = random.sample(teams, 2)
        winner = random.choice([t1, t2])
        fmt = random.choice(formats)
        venue = random.choice(venues)
        match_date = (base_date - timedelta(days=random.randint(1, 3650))).strftime("%Y-%m-%d")
        
        matches.append((match_id, match_date, venue, "City", fmt, "Men", t1, t2, winner, random.randint(1, 100), random.randint(1, 10)))
        
        # We will only generate detailed stats for a subset to save processing time, 
        # but we need to ensure player careers look realistic.
    
    # We will insert Matches using Team names directly to bypass the Team ID join complexity for the archive scale
    cursor.executemany("""
    INSERT OR IGNORE INTO Matches (match_id, date, venue, city, format, gender, team1_id, team2_id, winner, win_margin_runs, win_margin_wickets)
    VALUES (?, ?, ?, ?, ?, ?, (SELECT team_id FROM Teams WHERE name=?), (SELECT team_id FROM Teams WHERE name=?), (SELECT team_id FROM Teams WHERE name=?), ?, ?)
    """, matches)

    conn.commit()
    conn.close()
    print("Successfully expanded SQLite Database with thousands of matches, series, and leagues!")

if __name__ == "__main__":
    generate_massive_data()
