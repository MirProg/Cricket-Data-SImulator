import sqlite3
import re
import os

SOURCE_DB = r"C:\Users\seo\.local\bin\cricket_simulator\data\cricket_db.sqlite"
TARGET_DB = r"C:\Users\seo\.local\bin\cricket_simulator\data\master_archive.sqlite"

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

def parse_date(date_str):
    if not date_str: return "Unknown Year", "Unknown Month"
    
    year_match = re.search(r'\b(18|19|20)\d{2}\b', date_str)
    year = year_match.group(0) if year_match else "Unknown Year"
    
    month = "Unknown Month"
    for m in MONTHS:
        if m in date_str:
            month = m
            break
            
    return year, month

def migrate_db():
    if os.path.exists(TARGET_DB):
        os.remove(TARGET_DB)
        
    src = sqlite3.connect(SOURCE_DB)
    tgt = sqlite3.connect(TARGET_DB)
    
    # 1. Create Target Schema
    tgt.executescript("""
        CREATE TABLE Seasons (
            season_id TEXT PRIMARY KEY,
            year_string TEXT
        );
        CREATE TABLE Tournaments (
            tournament_id TEXT PRIMARY KEY,
            season_id TEXT,
            name TEXT,
            FOREIGN KEY(season_id) REFERENCES Seasons(season_id)
        );
        CREATE TABLE Matches (
            match_id TEXT PRIMARY KEY,
            tournament_id TEXT,
            season_id TEXT,
            month_string TEXT,
            title TEXT,
            date_string TEXT,
            venue TEXT,
            format TEXT,
            result TEXT,
            FOREIGN KEY(tournament_id) REFERENCES Tournaments(tournament_id),
            FOREIGN KEY(season_id) REFERENCES Seasons(season_id)
        );
    """)
    
    print("Migrating Matches and building Seasons/Tournaments...")
    src_matches = src.execute("SELECT match_id, tournament_id, title, date, venue, format, result FROM CAMatches")
    src_tournaments = dict(src.execute("SELECT tournament_id, name FROM CATournaments").fetchall())
    
    seasons_set = set()
    tournaments_inserted = set()
    
    matches_data = []
    
    for row in src_matches.fetchall():
        m_id, t_id, title, date_str, venue, fmt, result = row
        year, month = parse_date(date_str)
        
        # Fallback to tournament name for year if date doesn't have it
        t_name = src_tournaments.get(t_id, "Unknown Tournament")
        if year == "Unknown Year":
            y_match = re.search(r'\b(18|19|20)\d{2}\b', t_name)
            if y_match: year = y_match.group(0)
            
        season_id = f"season_{year}"
        if season_id not in seasons_set:
            tgt.execute("INSERT INTO Seasons (season_id, year_string) VALUES (?, ?)", (season_id, year))
            seasons_set.add(season_id)
            
        if t_id and t_id not in tournaments_inserted:
            tgt.execute("INSERT INTO Tournaments (tournament_id, season_id, name) VALUES (?, ?, ?)", (t_id, season_id, t_name))
            tournaments_inserted.add(t_id)
            
        matches_data.append((m_id, t_id, season_id, month, title, date_str, venue, fmt, result))
        
    tgt.executemany("""
        INSERT INTO Matches (match_id, tournament_id, season_id, month_string, title, date_string, venue, format, result)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, matches_data)
    
    print("Migrating Scorecards (Direct Copy)...")
    # Tables to direct copy
    tables_to_copy = ["CAInnings", "CAPlayerBattingScorecard", "CAPlayerBowlingScorecard", "CAFallOfWickets", "CAPlayers", "CATeams"]
    
    for table in tables_to_copy:
        print(f"  Copying {table}...")
        # Get schema
        schema_row = src.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'").fetchone()
        if schema_row and schema_row[0]:
            tgt.execute(schema_row[0])
            
            # Copy data
            src_data = src.execute(f"SELECT * FROM {table}").fetchall()
            placeholders = ",".join(["?"] * len(src_data[0])) if src_data else ""
            if placeholders:
                tgt.executemany(f"INSERT INTO {table} VALUES ({placeholders})", src_data)
                
    tgt.commit()
    src.close()
    tgt.close()
    print("ETL Migration Complete! Master Archive Database generated.")

if __name__ == "__main__":
    migrate_db()
