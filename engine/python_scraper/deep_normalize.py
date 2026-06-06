import sqlite3
import os
import re

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "master_archive.sqlite"))

def alter_schema(cursor):
    # Add columns if they don't exist
    columns_to_add = ['team1', 'team2', 'tournament', 'season', 'ground_name']
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(ScrapedMatches)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    
    for col in columns_to_add:
        if col not in existing_cols:
            cursor.execute(f"ALTER TABLE ScrapedMatches ADD COLUMN {col} TEXT")

def normalize_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Preparing schema...")
    alter_schema(cursor)
    conn.commit()
    
    print("Fetching matches...")
    cursor.execute("SELECT match_id, title, series, venue FROM ScrapedMatches")
    rows = cursor.fetchall()
    
    updates = []
    print(f"Normalizing {len(rows)} matches...")
    
    season_pattern = re.compile(r'\b((?:17|18|19|20)\d{2}(?:/\d{2,4})?)\b')
    
    for row in rows:
        match_id, title, series, venue = row
        title = title or ""
        series = series or ""
        venue = venue or ""
        
        # 1. Teams
        team1, team2 = "", ""
        if ' v ' in title:
            parts = title.split(' v ', 1)
        elif ' vs ' in title:
            parts = title.split(' vs ', 1)
        elif 'v' in title:
            # Dangerous fallback for old strings like EnglandvKent
            parts = title.split('v', 1)
        else:
            parts = [title]
            
        if len(parts) == 2:
            team1, team2 = parts[0].strip(), parts[1].strip()
        else:
            team1 = title.strip()
            
        # 2. Season & Tournament
        season = ""
        tournament = series
        s_match = season_pattern.search(series)
        if s_match:
            season = s_match.group(1)
            # Remove the season from the series to get the raw tournament name
            tournament = series.replace(season, "").replace("()", "").strip()
            
        # Clean up tournament name (remove trailing/leading spaces, excess spaces)
        tournament = re.sub(r'\s+', ' ', tournament).strip()
            
        # 3. Ground Name
        ground_name = venue
        if "on " in venue:
            ground_name = venue.split("on ")[0].strip()
            
        updates.append((team1, team2, tournament, season, ground_name, match_id))
        
    print("Executing mass UPDATE...")
    batch_size = 50000
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i+batch_size]
        cursor.executemany("""
            UPDATE ScrapedMatches 
            SET team1 = ?, team2 = ?, tournament = ?, season = ?, ground_name = ? 
            WHERE match_id = ?
        """, batch)
        conn.commit()
        print(f"Updated {i+len(batch)} / {len(updates)}")
        
    conn.close()
    print("Deep Normalization Complete!")

if __name__ == "__main__":
    normalize_database()
