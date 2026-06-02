import sqlite3
import uuid

DB_PATH = "cricmatrix.db"

def seed_database():
    print("[*] Seeding Database...")
    with sqlite3.connect(DB_PATH) as conn:
        # Create matches table
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
        
        # Insert high-quality mock matches
        matches_data = [
            (str(uuid.uuid4()), "2011-04-02", "Wankhede Stadium", "Mumbai", "ODI", "India", "Sri Lanka", "India", 0, 6),
            (str(uuid.uuid4()), "2024-06-29", "Kensington Oval", "Bridgetown", "T20I", "India", "South Africa", "India", 7, 0),
            (str(uuid.uuid4()), "2019-07-14", "Lord's", "London", "ODI", "England", "New Zealand", "England", 0, 0),
            (str(uuid.uuid4()), "2007-09-24", "Wanderers Stadium", "Johannesburg", "T20I", "India", "Pakistan", "India", 5, 0),
            (str(uuid.uuid4()), "2022-11-13", "MCG", "Melbourne", "T20I", "England", "Pakistan", "England", 0, 5),
            (str(uuid.uuid4()), "2015-03-29", "MCG", "Melbourne", "ODI", "Australia", "New Zealand", "Australia", 0, 7)
        ]
        
        # Clear existing mock data if re-running
        conn.execute("DELETE FROM matches")
        
        conn.executemany("""
            INSERT INTO matches 
            (match_id, date, venue, city, format, team1, team2, winner, win_margin_runs, win_margin_wickets)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, matches_data)
        
        print(f"[+] Successfully seeded {len(matches_data)} matches.")
        
        # Make sure canonical_players exists and has a mock count
        conn.execute("""
            CREATE TABLE IF NOT EXISTS canonical_players (
                canonical_id TEXT PRIMARY KEY,
                primary_name TEXT,
                nationality TEXT
            )
        """)

if __name__ == "__main__":
    seed_database()
