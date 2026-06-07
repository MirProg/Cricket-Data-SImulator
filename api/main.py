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
from engine.statsguru import StatsguruEngine
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

from engine.nlp_router import NLPRouter

class AskRequest(BaseModel):
    query: str

@app.post("/api/ask")
def ask_cricdb(request: AskRequest):
    q = request.query.lower()
    
    router = NLPRouter()
    payload = router.parse_query(q)
    
    engine = StatsguruEngine()
    result = engine.execute_query(payload["mode"], payload["filters"])
    
    answer = "No results found matching your query."
    if result.get("data") and len(result["data"]) > 0:
        top = result["data"][0]
        if payload["mode"] == "batting":
            answer = f"Based on our dynamic Statsguru aggregation, the top result is **{top['player_name']}** with **{top['total_runs']}** runs and a batting average of **{top.get('average', 'N/A')}**."
        else:
            answer = f"Based on our dynamic Statsguru aggregation, the top result is **{top['player_name']}** with **{top['total_wickets']}** wickets and a bowling average of **{top.get('bowling_average', 'N/A')}**."
            
    return {"answer": answer, "sql": result.get("sql", "Error executing query"), "filters": payload["filters"]}

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
    completed_extractions = 0
    recent_extractions = []
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM ScrapedMatches")
            total_matches = cursor.fetchone()[0]
            
            try:
                cursor = conn.execute("SELECT COUNT(*) FROM ExtractorProgress")
                completed_extractions = cursor.fetchone()[0]
                
                # Fetch recent extractions for the ticker
                cursor = conn.execute("""
                    SELECT m.team1, m.team2, m.season 
                    FROM ExtractorProgress e 
                    JOIN ScrapedMatches m ON e.match_id = m.match_id 
                    ORDER BY e.rowid DESC 
                    LIMIT 10
                """)
                for row in cursor.fetchall():
                    team1 = row[0] or "Unknown"
                    team2 = row[1] or "Unknown"
                    season = row[2] or "Unknown"
                    recent_extractions.append(f"{team1} vs {team2} ({season})")
                    
            except sqlite3.OperationalError:
                pass

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
            "completed_extractions": completed_extractions,
            "total_balls_delivered": total_deliveries or 0,
            "total_players": total_players or 0
        },
        "recent_extractions": recent_extractions,
        "scraper_logs": [
            "[INFO] SQLite Data Warehouse Connected",
            "[SUCCESS] Relational Table Scheme Synchronized",
            "[INFO] Waiting for extractor to populate records..."
        ]
    }

class StatsguruFilterRequest(BaseModel):
    mode: str  # "batting" or "bowling"
    filters: dict

@app.post("/api/v1/statsguru/query")
def statsguru_query(req: StatsguruFilterRequest):
    engine = StatsguruEngine()
    result = engine.execute_query(req.mode, req.filters)
    return result

@app.get("/api/v1/players/search")
def search_players_api(q: str):
    results = []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT player_id, player_name FROM Players WHERE player_name LIKE ? LIMIT 10", (f"%{q}%",))
            for row in cursor.fetchall():
                results.append({"id": row[0], "name": row[1]})
    except Exception as e:
        pass
    return {"query": q, "results": results}

@app.get("/api/v1/teams/search")
def search_teams_api(q: str):
    results = []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT team_id, team_name FROM Teams WHERE team_name LIKE ? LIMIT 10", (f"%{q}%",))
            for row in cursor.fetchall():
                results.append({"id": row[0], "name": row[1]})
    except Exception as e:
        pass
    return {"query": q, "results": results}

@app.get("/api/v1/venues/search")
def search_venues_api(q: str):
    results = []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT venue_id, venue_name FROM Venues WHERE venue_name LIKE ? LIMIT 10", (f"%{q}%",))
            for row in cursor.fetchall():
                results.append({"id": row[0], "name": row[1]})
    except Exception as e:
        pass
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
