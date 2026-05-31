import sqlite3
import os
import random
from datetime import datetime, timedelta

def seed_db():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'cricket_db.sqlite'))
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables if they don't exist (they should, but just in case)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Matches (
        match_id TEXT PRIMARY KEY,
        date TEXT,
        team_a TEXT,
        team_b TEXT,
        winner TEXT,
        margin TEXT,
        format TEXT,
        venue TEXT
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Player_Match_Stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id TEXT,
        player_name TEXT,
        team TEXT,
        runs_scored INTEGER,
        balls_faced INTEGER,
        wickets_taken INTEGER,
        runs_conceded INTEGER,
        overs_bowled REAL
    )""")
    
    # Ensure Teams exist first
    teams = [
        ("T1", "India"), ("T2", "Australia"), ("T3", "England"), 
        ("T4", "South Africa"), ("T5", "New Zealand"), ("T6", "Pakistan")
    ]
    cursor.executemany("INSERT OR IGNORE INTO Teams (team_id, name) VALUES (?, ?)", teams)

    # Generate Players and Career Stats
    players_data = []
    career_stats = []
    
    player_id_counter = 1
    for t_id, t_name in teams:
        for i in range(1, 12): # 11 players per team
            p_id = f"P{player_id_counter:03d}"
            p_name = f"{t_name} Player {i}"
            players_data.append((p_id, p_name))
            player_id_counter += 1
            
    cursor.executemany("INSERT OR IGNORE INTO Players (player_id, name) VALUES (?, ?)", players_data)
    
    # We will just write a simplified query for PlayerCareerStats
    cursor.execute("DROP TABLE IF EXISTS PlayerCareerStats")
    cursor.execute("""
    CREATE TABLE PlayerCareerStats (
        player_id TEXT,
        format TEXT,
        matches INTEGER,
        bat_runs INTEGER,
        bat_avg REAL,
        highest_score INTEGER,
        bowl_wickets INTEGER,
        bowl_avg REAL,
        bowl_econ REAL,
        team_name TEXT
    )""")
    
    simple_career = []
    for p_id, p_name in players_data:
        team_name = p_name.rsplit(" ", 2)[0]
        matches = random.randint(10, 150)
        bat_runs = random.randint(200, 8000)
        bat_avg = round(random.uniform(15.0, 60.0), 2)
        highest_score = random.randint(30, 200)
        bowl_wickets = random.randint(0, 400)
        bowl_avg = round(random.uniform(20.0, 50.0), 2) if bowl_wickets > 0 else 0.0
        bowl_econ = round(random.uniform(4.0, 9.0), 2)
        simple_career.append((p_id, "All Formats", matches, bat_runs, bat_avg, highest_score, bowl_wickets, bowl_avg, bowl_econ, team_name))
        
    cursor.executemany("INSERT INTO PlayerCareerStats VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", simple_career)
    
    match_data = []
    stat_data = []
    base_date = datetime.now()
    
    for i in range(100):
        match_id = f"mock_match_{i}"
        t1, t2 = random.sample(teams, 2)
        winner = random.choice([t1[0], t2[0]])
        fmt = random.choice(["T20I", "ODI", "Test"])
        venue = random.choice(["Lord's", "MCG", "Wankhede", "Eden Gardens"])
        match_date = (base_date - timedelta(days=random.randint(1, 365))).strftime("%Y-%m-%d")
        
        match_data.append((match_id, match_date, venue, "City", fmt, "Men", t1[0], t2[0], winner, random.randint(1,50), 0))
        
        # Stats
        for j in range(11):
            p1 = f"{t1[1]} Player {j+1}"
            p2 = f"{t2[1]} Player {j+1}"
            p1_runs = random.randint(0, 120)
            p1_balls = int(p1_runs * random.uniform(0.6, 1.5))
            stat_data.append((match_id, p1, t1[1], p1_runs, p1_balls, random.randint(0,4), random.randint(10, 60), 4.0))
            p2_runs = random.randint(0, 120)
            p2_balls = int(p2_runs * random.uniform(0.6, 1.5))
            stat_data.append((match_id, p2, t2[1], p2_runs, p2_balls, random.randint(0,4), random.randint(10, 60), 4.0))

    cursor.executemany("""
    INSERT OR REPLACE INTO Matches (match_id, date, venue, city, format, gender, team1_id, team2_id, winner, win_margin_runs, win_margin_wickets)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, match_data)
    
    cursor.executemany("""
    INSERT INTO Player_Match_Stats (match_id, player_name, team, runs_scored, balls_faced, wickets_taken, runs_conceded, overs_bowled)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, stat_data)
    
    conn.commit()
    conn.close()
    print("Database seeded successfully with mock data!")

if __name__ == "__main__":
    seed_db()
