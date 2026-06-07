import sqlite3
import os
import time

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "master_archive.sqlite")

def build_entities():
    print("Connecting to database...")
    # Using a 30 second timeout in case the extractor is finishing up
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cursor = conn.cursor()

    print("Creating Relational Entity Tables...")

    # 1. Players Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Players (
            player_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT UNIQUE NOT NULL
        )
    """)

    # 2. Teams Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Teams (
            team_id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_name TEXT UNIQUE NOT NULL
        )
    """)

    # 3. Venues Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Venues (
            venue_id INTEGER PRIMARY KEY AUTOINCREMENT,
            venue_name TEXT UNIQUE NOT NULL
        )
    """)

    conn.commit()

    print("Extracting unique Players from ScrapedBatting and ScrapedBowling...")
    cursor.execute("""
        INSERT OR IGNORE INTO Players (player_name)
        SELECT DISTINCT player_name FROM ScrapedBatting
        UNION
        SELECT DISTINCT player_name FROM ScrapedBowling
    """)
    conn.commit()
    print(f"Extracted players. Total unique players: {cursor.execute('SELECT COUNT(*) FROM Players').fetchone()[0]}")

    print("Extracting unique Teams from ScrapedMatches and ScrapedInnings...")
    cursor.execute("""
        INSERT OR IGNORE INTO Teams (team_name)
        SELECT DISTINCT team1 FROM ScrapedMatches WHERE team1 IS NOT NULL AND team1 != ''
        UNION
        SELECT DISTINCT team2 FROM ScrapedMatches WHERE team2 IS NOT NULL AND team2 != ''
        UNION
        SELECT DISTINCT team_name FROM ScrapedInnings WHERE team_name IS NOT NULL AND team_name != ''
    """)
    conn.commit()
    print(f"Extracted teams. Total unique teams: {cursor.execute('SELECT COUNT(*) FROM Teams').fetchone()[0]}")

    print("Extracting unique Venues from ScrapedMatches...")
    cursor.execute("""
        INSERT OR IGNORE INTO Venues (venue_name)
        SELECT DISTINCT ground_name FROM ScrapedMatches WHERE ground_name IS NOT NULL AND ground_name != ''
    """)
    conn.commit()
    print(f"Extracted venues. Total unique venues: {cursor.execute('SELECT COUNT(*) FROM Venues').fetchone()[0]}")

    # (Optional) Future step: Add player_id, team_id, venue_id foreign keys to ScrapedBatting/ScrapedMatches 
    # and UPDATE them based on the text matches. We will do this as a final sweep later.

    conn.close()
    print("Relational Entity sweep complete!")

if __name__ == "__main__":
    print("=== Relational Entity Builder ===")
    print("WARNING: Only run this after the mass extractor has finished all 323,000 matches!")
    print("Starting in 5 seconds...")
    time.sleep(5)
    build_entities()
