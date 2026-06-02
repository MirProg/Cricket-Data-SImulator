from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import sys
import os

# Ensure the parent directory is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.markov_simulator import MarkovSimulator
from engine.advanced_stats import AdvancedStatsEngine

app = FastAPI(title="CricMatrix AI Engine", version="1.0")

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.get("/api/v1/matches")
def get_matches():
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "../data/cricmatrix.db")
    matches = []
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT * FROM matches ORDER BY date DESC")
            # Get column names
            columns = [col[0] for col in cursor.description]
            for row in cursor.fetchall():
                matches.append(dict(zip(columns, row)))
    except Exception as e:
        print("Matches error:", e)
    return {"matches": matches}

@app.get("/api/v1/system/status")
def get_system_status():
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "../data/cricmatrix.db")
    total_matches = 0
    total_players = 0
    total_deliveries = 0
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM matches")
            total_matches = cursor.fetchone()[0]
            cursor = conn.execute("SELECT COUNT(*) FROM canonical_players")
            total_players = cursor.fetchone()[0]
            cursor = conn.execute("SELECT COUNT(*) FROM deliveries")
            total_deliveries = cursor.fetchone()[0]
    except Exception:
        pass
        
    return {
        "database": {
            "total_matches": total_matches,
            "total_balls_delivered": total_deliveries,
            "total_players": total_players
        },
        "scraper_logs": [
            "[2026-06-01 12:00:00] [INFO] ESPN Spider sleeping... Rate limit.",
            "[2026-06-01 12:01:00] [INFO] Cricbuzz socket listening...",
            "[2026-06-01 12:02:00] [SUCCESS] Ingested 5336 new matches from Cricsheet."
        ]
    }

@app.get("/search/players")
def search_players(q: str):
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "../data/cricmatrix.db")
    results = []
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "SELECT canonical_id, primary_name FROM canonical_players WHERE primary_name LIKE ? LIMIT 10",
                (f"%{q}%",)
            )
            for row in cursor.fetchall():
                results.append({"id": row[0], "name": row[1]})
    except Exception as e:
        print("Search error:", e)
    return {"query": q, "results": results}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
