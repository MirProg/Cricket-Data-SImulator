import sqlite3
import re
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/archive", tags=["Archive"])

DB_PATH = r"C:\Users\seo\.local\bin\cricket_simulator\data\master_archive.sqlite"

@router.get("/seasons")
def get_seasons():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT DISTINCT venue, series FROM ScrapedMatches")
            rows = cursor.fetchall()
            years = set()
            for venue, series in rows:
                m1 = re.search(r'\b(17|18|19|20)\d{2}\b', venue or "")
                m2 = re.search(r'\b(17|18|19|20)\d{2}\b', series or "")
                if m1: years.add(m1.group(0))
                elif m2: years.add(m2.group(0))
            
            seasons = [{"id": y, "year": y} for y in sorted(list(years), reverse=True)]
            return {"seasons": seasons}
    except Exception as e:
        return {"error": str(e)}

@router.get("/seasons/{season_id}/matches")
def get_season_matches(season_id: str):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT * FROM ScrapedMatches WHERE venue LIKE ? OR series LIKE ? ORDER BY match_id DESC", (f"%{season_id}%", f"%{season_id}%"))
            cols = [c[0] for c in cursor.description]
            matches = [dict(zip(cols, row)) for row in cursor.fetchall()]
            
            for m in matches:
                # Add synthetic fields for frontend
                date_match = re.search(r'on (\d+(?:st|nd|rd|th)? [A-Za-z]+ \d{4})', m.get('series') or "")
                if not date_match:
                    date_match = re.search(r'on (\d+(?:st|nd|rd|th)? [A-Za-z]+ \d{4})', m.get('venue') or "")
                    
                m['date_string'] = date_match.group(1) if date_match else "Date Unknown"
                m['month_string'] = ""
                m['format'] = "Match"
                
                if not m['result']:
                    m['result'] = m.get('series') if 'won' in (m.get('series') or "").lower() or 'draw' in (m.get('series') or "").lower() else "Result Pending"
            return {"matches": matches}
    except Exception as e:
        return {"error": str(e)}

@router.get("/matches/{match_id}")
def get_match_details(match_id: str):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT * FROM ScrapedMatches WHERE match_id = ?", (match_id,))
            m_row = cursor.fetchone()
            if not m_row: return {"error": "Match not found"}
            
            m_cols = [c[0] for c in cursor.description]
            metadata = dict(zip(m_cols, m_row))
            
            # ScrapedBatting: id, match_id, innings_number, player_name, dismissal, runs, balls, mins, fours, sixes
            try:
                cursor = conn.execute("SELECT * FROM ScrapedBatting WHERE match_id = ? ORDER BY innings_number, id", (match_id,))
                bat_cols = [c[0] for c in cursor.description]
                batting = [dict(zip(bat_cols, r)) for r in cursor.fetchall()]
            except sqlite3.OperationalError:
                batting = [] # Table might not exist if extractor hasn't run yet
                
            # ScrapedBowling: id, match_id, innings_number, player_name, overs, maidens, runs, wickets, wides, no_balls
            try:
                cursor = conn.execute("SELECT * FROM ScrapedBowling WHERE match_id = ? ORDER BY innings_number, id", (match_id,))
                bowl_cols = [c[0] for c in cursor.description]
                bowling = [dict(zip(bowl_cols, r)) for r in cursor.fetchall()]
            except sqlite3.OperationalError:
                bowling = []
            
            max_inn = 0
            if batting: max_inn = max(max_inn, max(b['innings_number'] for b in batting))
            if bowling: max_inn = max(max_inn, max(b['innings_number'] for b in bowling))
            
            scorecards = []
            for i in range(1, max_inn + 1):
                inn_bat = [b for b in batting if b['innings_number'] == i]
                inn_bowl = [b for b in bowling if b['innings_number'] == i]
                
                scorecards.append({
                    "details": {"innings_number": i, "batting_team": f"Innings {i}"},
                    "batting": inn_bat,
                    "bowling": inn_bowl,
                    "fow": []
                })
                
            return {
                "metadata": metadata,
                "scorecards": scorecards
            }
    except Exception as e:
        return {"error": str(e)}
