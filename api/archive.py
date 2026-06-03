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
            cursor = conn.execute("SELECT season_id, year_string FROM Seasons ORDER BY year_string DESC")
            seasons = [{"id": row[0], "year": row[1]} for row in cursor.fetchall()]
            return {"seasons": seasons}
    except Exception as e:
        return {"error": str(e)}

@router.get("/seasons/{season_id}/tournaments")
def get_season_tournaments(season_id: str):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT tournament_id, name FROM Tournaments WHERE season_id = ?", (season_id,))
            tournaments = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
            return {"tournaments": tournaments}
    except Exception as e:
        return {"error": str(e)}

@router.get("/tournaments/{tournament_id}/matches")
def get_tournament_matches(tournament_id: str):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("""
                SELECT match_id, title, date_string, format, venue, result, month_string
                FROM Matches WHERE tournament_id = ? ORDER BY date_string DESC
            """, (tournament_id,))
            cols = [c[0] for c in cursor.description]
            matches = [dict(zip(cols, row)) for row in cursor.fetchall()]
            return {"matches": matches}
    except Exception as e:
        return {"error": str(e)}

@router.get("/matches/{match_id}")
def get_match_details(match_id: str):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT * FROM Matches WHERE match_id = ?", (match_id,))
            m_row = cursor.fetchone()
            if not m_row: return {"error": "Match not found"}
            
            m_cols = [c[0] for c in cursor.description]
            metadata = dict(zip(m_cols, m_row))
            
            # Get Innings
            cursor = conn.execute("SELECT * FROM CAInnings WHERE match_id = ? ORDER BY innings_number", (match_id,))
            i_cols = [c[0] for c in cursor.description]
            innings = [dict(zip(i_cols, r)) for r in cursor.fetchall()]
            
            scorecards = []
            for inn in innings:
                inn_id = inn["id"]
                
                # Batting
                cursor = conn.execute("""
                    SELECT p.name, b.dismissal_text, b.runs, b.balls, b.fours, b.sixes, b.strike_rate
                    FROM CAPlayerBattingScorecard b
                    LEFT JOIN CAPlayers p ON b.player_id = p.player_id
                    WHERE b.innings_id = ?
                """, (inn_id,))
                bat_cols = [c[0] for c in cursor.description]
                batting = [dict(zip(bat_cols, r)) for r in cursor.fetchall()]
                
                # Bowling
                cursor = conn.execute("""
                    SELECT p.name, b.overs, b.maidens, b.runs, b.wickets, b.econ
                    FROM CAPlayerBowlingScorecard b
                    LEFT JOIN CAPlayers p ON b.player_id = p.player_id
                    WHERE b.innings_id = ?
                """, (inn_id,))
                bowl_cols = [c[0] for c in cursor.description]
                bowling = [dict(zip(bowl_cols, r)) for r in cursor.fetchall()]
                
                # FOW
                cursor = conn.execute("""
                    SELECT f.wicket_num, f.score, f.overs, p.name
                    FROM CAFallOfWickets f
                    LEFT JOIN CAPlayers p ON f.player_out_id = p.player_id
                    WHERE f.innings_id = ?
                    ORDER BY f.wicket_num
                """, (inn_id,))
                fow_cols = [c[0] for c in cursor.description]
                fow = [dict(zip(fow_cols, r)) for r in cursor.fetchall()]
                
                scorecards.append({
                    "details": inn,
                    "batting": batting,
                    "bowling": bowling,
                    "fow": fow
                })
                
            return {
                "metadata": metadata,
                "scorecards": scorecards
            }
    except Exception as e:
        return {"error": str(e)}
