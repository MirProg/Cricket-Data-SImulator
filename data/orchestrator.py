import sqlite3
import hashlib
import logging
import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - ORCHESTRATOR - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = 'data/cricket_db.sqlite'

def init_registry():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS MatchRegistry (
            universal_match_id TEXT PRIMARY KEY,
            team1 TEXT,
            team2 TEXT,
            match_date TEXT,
            format TEXT,
            ca_id TEXT,
            cricbuzz_id TEXT,
            espn_id TEXT
        )
    ''')
    conn.commit()
    conn.close()

def normalize_team(team):
    if not team: return "Unknown"
    # Basic normalization map
    team = team.strip()
    norm = {
        "IND": "India", "AUS": "Australia", "ENG": "England", "SA": "South Africa",
        "PAK": "Pakistan", "NZ": "New Zealand", "SL": "Sri Lanka", "WI": "West Indies",
        "BAN": "Bangladesh", "AFG": "Afghanistan"
    }
    return norm.get(team, team)

def register_match(team1, team2, date, format_str, source, source_id):
    """
    Registers a match. Returns True if this is a NEW match that should be processed.
    Returns False if it's a DUPLICATE already in the DB from another source.
    """
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    
    t1 = normalize_team(team1)
    t2 = normalize_team(team2)
    # Ensure alphabetical order for signature
    teams = sorted([t1.lower(), t2.lower()])
    
    # Create deterministic signature
    sig_str = f"{teams[0]}_{teams[1]}_{date}_{format_str}".encode('utf-8')
    u_id = hashlib.md5(sig_str).hexdigest()
    
    cursor.execute("SELECT * FROM MatchRegistry WHERE universal_match_id = ?", (u_id,))
    row = cursor.fetchone()
    
    if row:
        # Match already exists! Link the new source ID but return False (skip parsing)
        update_col = f"{source.lower()}_id"
        if update_col in ['ca_id', 'cricbuzz_id', 'espn_id']:
            cursor.execute(f"UPDATE MatchRegistry SET {update_col} = ? WHERE universal_match_id = ?", (source_id, u_id))
            conn.commit()
        conn.close()
        logger.info(f"Duplicate Match Detected: {t1} vs {t2} on {date}. Suppressed overlapping parse from {source}.")
        return False
    else:
        # New Match!
        ca = source_id if source.lower() == 'ca' else None
        cb = source_id if source.lower() == 'cricbuzz' else None
        espn = source_id if source.lower() == 'espn' else None
        
        cursor.execute("""
            INSERT INTO MatchRegistry (universal_match_id, team1, team2, match_date, format, ca_id, cricbuzz_id, espn_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (u_id, t1, t2, date, format_str, ca, cb, espn))
        conn.commit()
        conn.close()
        return True

# Initialize on import
init_registry()
