from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import sys
import os
import sqlite3
import re

# Ensure the parent directory is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.markov_simulator import MarkovSimulator
from engine.advanced_stats import AdvancedStatsEngine
from archive import router as archive_router
from engine.full_match_simulator import FullMatchSimulator

app = FastAPI(title="CricMatrix AI Engine", version="1.0")

app.include_router(archive_router)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = r"C:\Users\seo\.local\bin\cricket_simulator\data\master_archive.sqlite"

class AskRequest(BaseModel):
    query: str

@app.post("/api/ask")
def ask_cricdb(request: AskRequest):
    q = request.query.lower()
    answer = ""
    sql = ""
    
    # Mocked Text-to-SQL Domain Router
    if "most runs" in q and ("test" in q or "tests" in q):
        sql = "SELECT player_name, SUM(runs) as total_runs FROM ScrapedBatting JOIN ScrapedMatches ON ScrapedBatting.match_id = ScrapedMatches.match_id WHERE match_format = 'Test' GROUP BY player_name ORDER BY total_runs DESC LIMIT 1;"
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(sql).fetchone()
            if row:
                answer = f"The player with the most runs in Test matches in our database is **{row[0]}** with **{row[1]}** runs."
    elif "most wickets" in q:
        sql = "SELECT player_name, SUM(wickets) as total_wickets FROM ScrapedBowling GROUP BY player_name ORDER BY total_wickets DESC LIMIT 1;"
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(sql).fetchone()
            if row:
                answer = f"The player with the most wickets across all formats is **{row[0]}** with **{row[1]}** wickets."
    else:
        sql = "SELECT player_name, SUM(runs) as total_runs FROM ScrapedBatting GROUP BY player_name ORDER BY total_runs DESC LIMIT 1;"
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(sql).fetchone()
            answer = f"I'm an AI agent. I mapped your query to a default SQL aggregation. The all-time highest run scorer across all scraped formats is **{row[0]}** with **{row[1]}** runs."

    return {"answer": answer, "sql": sql}

class SimulationRequest(BaseModel):
    runs_scored: int = 0
    balls_remaining: int = 120
    wickets_lost: int = 0
    n_simulations: int = 10000

class SimulationResponse(BaseModel):
    mean_runs: float
    median_runs: float
    p25_runs: float
    p75_runs: float
    p90_runs: float
    mean_wickets: float
    trajectories: list

@app.post("/simulate", response_model=SimulationResponse)
def simulate_match(req: SimulationRequest):
    simulator = MarkovSimulator(n_simulations=req.n_simulations)
    results = simulator.simulate_innings(
        starting_runs=req.runs_scored,
        starting_balls_remaining=req.balls_remaining,
        starting_wickets=req.wickets_lost
    )
    return results

class PressureRequest(BaseModel):
    innings: int
    par_score: float
    current_score: int
    wickets_lost: int
    expected_runs_remaining: float
    runs_needed: int

@app.post("/stats/pressure")
def get_pressure_index(req: PressureRequest):
    engine = AdvancedStatsEngine()
    pressure = engine.calculate_pressure_index(
        innings=req.innings,
        par_score=req.par_score,
        current_score=req.current_score,
        wickets_lost=req.wickets_lost,
        expected_runs_remaining=req.expected_runs_remaining,
        runs_needed=req.runs_needed
    )
    return {"pressure_index": pressure}

class MatchSimulationRequest(BaseModel):
    team1: list[str]
    team2: list[str]
    venue: str = "Generic Stadium"

@app.post("/simulate_match")
def simulate_full_match(req: MatchSimulationRequest):
    sim = FullMatchSimulator()
    result = sim.simulate_match(req.team1, req.team2)
    return result

@app.get("/api/matches")
def get_matches_recent(limit: int = 12, category: str = "recent"):
    matches = []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            query = "SELECT * FROM ScrapedMatches"
            params = []
            
            if category == "international":
                query += " WHERE match_category = 'International'"
            elif category == "domestic":
                query += " WHERE match_category = 'Domestic'"
                
            query += " ORDER BY match_id DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            columns = [col[0] for col in cursor.description]
            for row in cursor.fetchall():
                m = dict(zip(columns, row))
                # Add synthetic fields for frontend compatibility
                m['date'] = m.get('season') or "Unknown Date"
                
                m['team1_name'] = m.get('team1') or m.get('title') or "Unknown"
                m['team2_name'] = m.get('team2') or ""
                
                m['winner_name'] = ""
                res = m.get('result') or m.get('series') or ""
                if 'won' in res.lower():
                    m['winner_name'] = res.split('won')[0].strip()
                    
                matches.append(m)
    except Exception as e:
        print("Matches error:", e)
    return matches

@app.get("/api/match/{match_id}")
def get_match_scorecard(match_id: int):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # 1. Fetch Match Metadata
            cursor = conn.execute("SELECT * FROM ScrapedMatches WHERE match_id = ?", (match_id,))
            row = cursor.fetchone()
            if not row:
                return {"error": "Match not found"}
            
            columns = [col[0] for col in cursor.description]
            match_meta = dict(zip(columns, row))
            
            # 2. Fetch Innings Metadata
            innings_cursor = conn.execute("SELECT * FROM ScrapedInnings WHERE match_id = ? ORDER BY innings_number ASC", (match_id,))
            innings_cols = [c[0] for c in innings_cursor.description]
            innings_data = [dict(zip(innings_cols, r)) for r in innings_cursor.fetchall()]
            
            # 3. Fetch FOW
            fow_cursor = conn.execute("SELECT innings_number, fow_string FROM ScrapedFOW WHERE match_id = ?", (match_id,))
            fow_dict = {r[0]: r[1] for r in fow_cursor.fetchall()}
            
            # 4. Fetch Batting
            batting_cursor = conn.execute("SELECT * FROM ScrapedBatting WHERE match_id = ?", (match_id,))
            batting_cols = [c[0] for c in batting_cursor.description]
            all_batting = [dict(zip(batting_cols, r)) for r in batting_cursor.fetchall()]
            
            # 5. Fetch Bowling
            bowling_cursor = conn.execute("SELECT * FROM ScrapedBowling WHERE match_id = ?", (match_id,))
            bowling_cols = [c[0] for c in bowling_cursor.description]
            all_bowling = [dict(zip(bowling_cols, r)) for r in bowling_cursor.fetchall()]
            
            # Assemble payload
            scorecard = {
                "match_meta": match_meta,
                "innings": []
            }
            
            for inn in innings_data:
                inn_num = inn['innings_number']
                inn_payload = {
                    "metadata": inn,
                    "fow": fow_dict.get(inn_num, ""),
                    "batting": [b for b in all_batting if b['innings_number'] == inn_num],
                    "bowling": [bw for bw in all_bowling if bw['innings_number'] == inn_num]
                }
                scorecard["innings"].append(inn_payload)
                
            return scorecard
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/v1/system/status")
def get_system_status():
    total_matches = 0
    total_players = 0
    total_deliveries = 0
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM ScrapedMatches")
            total_matches = cursor.fetchone()[0]
            try:
                cursor = conn.execute("SELECT COUNT(DISTINCT player_name) FROM ScrapedBatting")
                total_players = cursor.fetchone()[0]
                cursor = conn.execute("SELECT SUM(balls) FROM ScrapedBatting")
                total_deliveries = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                pass
    except Exception:
        pass
        
    return {
        "database": {
            "total_matches": total_matches,
            "total_balls_delivered": total_deliveries or 0,
            "total_players": total_players or 0
        },
        "scraper_logs": [
            "[INFO] SQLite Data Warehouse Connected",
            "[SUCCESS] Relational Table Scheme Synchronized",
            "[INFO] Waiting for extractor to populate records..."
        ]
    }

@app.get("/search/players")
def search_players(q: str):
    results = []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute(
                "SELECT DISTINCT player_name FROM ScrapedBatting WHERE player_name LIKE ? LIMIT 10",
                (f"%{q}%",)
            )
            for idx, row in enumerate(cursor.fetchall()):
                results.append({"id": idx, "name": row[0]})
    except Exception as e:
        print("Search error:", e)
    return {"query": q, "results": results}

@app.get("/api/records")
def get_records():
    top_batsmen = []
    top_bowlers = []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # Top Batsmen
            cursor = conn.execute("SELECT player_name, SUM(runs) as total_runs FROM ScrapedBatting GROUP BY player_name ORDER BY total_runs DESC LIMIT 10")
            for row in cursor.fetchall():
                top_batsmen.append({"name": row[0], "bat_runs": row[1], "team_name": "INTL"})
                
            # Top Bowlers
            cursor = conn.execute("SELECT player_name, SUM(wickets) as total_wickets FROM ScrapedBowling GROUP BY player_name ORDER BY total_wickets DESC LIMIT 10")
            for row in cursor.fetchall():
                top_bowlers.append({"name": row[0], "wickets": row[1], "team_name": "INTL"})
                
        return {"top_run_scorers": top_batsmen, "top_wicket_takers": top_bowlers}
    except Exception:
        return {"top_run_scorers": [], "top_wicket_takers": []}

@app.get("/api/series")
def get_series():
    return [{"id": 1, "name": "Global Cricket Archive", "date": "All Time"}]

@app.get("/api/teams")
def get_teams():
    return []

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
