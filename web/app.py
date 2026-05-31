import os
import sys
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import torch
import logging
import sqlite3

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai.ml_pipeline import AdvancedMatchPredictor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Cricket Predictor")

# Add CORS middleware to allow Next.js on port 3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load PyTorch Model Globally
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
try:
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'models', 'advanced_predictor.pth'))
    model = AdvancedMatchPredictor().to(device)
    model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
    model.eval()
    logger.info("Successfully loaded AdvancedMatchPredictor Transformer!")
except Exception as e:
    logger.error(f"Failed to load model: {e}")
    model = None

class PredictionRequest(BaseModel):
    team_a: str
    team_b: str

def get_db():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'cricket_db.sqlite'))
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/api/matches")
async def get_recent_matches(limit: int = 10):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.match_id, m.date, m.format, m.venue, m.win_margin_runs,
               t1.name as team1_name, t2.name as team2_name, tw.name as winner_name
        FROM Matches m
        LEFT JOIN Teams t1 ON m.team1_id = t1.team_id
        LEFT JOIN Teams t2 ON m.team2_id = t2.team_id
        LEFT JOIN Teams tw ON m.winner = tw.team_id
        ORDER BY m.date DESC LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/match/{match_id}")
async def get_match_details(match_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.match_id, m.date, m.format, m.venue, m.win_margin_runs,
               t1.name as team1_name, t2.name as team2_name, tw.name as winner_name
        FROM Matches m
        LEFT JOIN Teams t1 ON m.team1_id = t1.team_id
        LEFT JOIN Teams t2 ON m.team2_id = t2.team_id
        LEFT JOIN Teams tw ON m.winner = tw.team_id
        WHERE m.match_id = ?
    """, (match_id,))
    match_info = cursor.fetchone()
    
    if not match_info:
        conn.close()
        return {"error": "Match not found"}
        
    cursor.execute("""
        SELECT player_name, team, runs_scored, balls_faced, wickets_taken, runs_conceded, overs_bowled 
        FROM Player_Match_Stats 
        WHERE match_id = ?
    """, (match_id,))
    stats = cursor.fetchall()
    conn.close()
    
    return {
        "info": dict(match_info),
        "scorecard": [dict(s) for s in stats]
    }

@app.get("/api/player/{player_name}")
async def get_player_stats(player_name: str):
    conn = get_db()
    cursor = conn.cursor()
    # Decode URL encoded name if needed
    decoded_name = player_name.replace("%20", " ")
    
    # We query the mock PlayerCareerStats we generated (but we only have it by player_id actually).
    # Wait, our seed script created PlayerCareerStats using player_id, but we only pass player_name around in Player_Match_Stats.
    # Let's join Players to get the ID.
    cursor.execute("""
        SELECT p.name, c.* 
        FROM Players p
        JOIN PlayerCareerStats c ON p.player_id = c.player_id
        WHERE p.name = ?
    """, (decoded_name,))
    row = cursor.fetchone()
    
    if not row:
        # Fallback to aggregating from Player_Match_Stats if career stats table doesn't have them
        cursor.execute("""
            SELECT player_name as name, team as team_name, count(match_id) as matches, 
                   sum(runs_scored) as bat_runs, sum(wickets_taken) as bowl_wickets
            FROM Player_Match_Stats
            WHERE player_name = ?
            GROUP BY player_name
        """, (decoded_name,))
        row = cursor.fetchone()
        
    conn.close()
    return dict(row) if row else {"error": "Player not found"}

@app.get("/api/records")
async def get_global_records():
    conn = get_db()
    cursor = conn.cursor()
    
    records = {}
    
    cursor.execute("""
        SELECT p.name, c.bat_runs, c.matches, c.team_name 
        FROM PlayerCareerStats c JOIN Players p ON c.player_id = p.player_id
        ORDER BY c.bat_runs DESC LIMIT 5
    """)
    records["top_run_scorers"] = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("""
        SELECT p.name, c.bowl_wickets, c.matches, c.team_name 
        FROM PlayerCareerStats c JOIN Players p ON c.player_id = p.player_id
        ORDER BY c.bowl_wickets DESC LIMIT 5
    """)
    records["top_wicket_takers"] = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("""
        SELECT p.name, c.bat_avg, c.matches, c.team_name 
        FROM PlayerCareerStats c JOIN Players p ON c.player_id = p.player_id
        WHERE c.matches > 20
        ORDER BY c.bat_avg DESC LIMIT 5
    """)
    records["highest_averages"] = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return records

@app.get("/api/stats/top-batsmen")
async def get_top_batsmen(limit: int = 10):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT player_name, team, sum(runs_scored) as total_runs, sum(balls_faced) as total_balls 
        FROM Player_Match_Stats 
        GROUP BY player_name, team 
        ORDER BY total_runs DESC LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/archives/{year}")
async def get_matches_by_year(year: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.match_id, m.date, m.format, m.venue, m.win_margin_runs,
               t1.name as team1_name, t2.name as team2_name, tw.name as winner_name
        FROM Matches m
        LEFT JOIN Teams t1 ON m.team1_id = t1.team_id
        LEFT JOIN Teams t2 ON m.team2_id = t2.team_id
        LEFT JOIN Teams tw ON m.winner = tw.team_id
        WHERE m.date LIKE ?
        ORDER BY m.date DESC LIMIT 50
    """, (f"{year}-%",))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/team/{team_name}")
async def get_team_matches(team_name: str):
    conn = get_db()
    cursor = conn.cursor()
    decoded_name = team_name.replace("%20", " ")
    
    # Capitalize for basic matching (e.g. 'india' -> 'India')
    formatted_name = decoded_name.title()
    if formatted_name.lower() == 'new-zealand': formatted_name = 'New Zealand'
    elif formatted_name.lower() == 'south-africa': formatted_name = 'South Africa'
    
    cursor.execute("""
        SELECT m.match_id, m.date, m.format, m.venue, m.win_margin_runs,
               t1.name as team1_name, t2.name as team2_name, tw.name as winner_name
        FROM Matches m
        LEFT JOIN Teams t1 ON m.team1_id = t1.team_id
        LEFT JOIN Teams t2 ON m.team2_id = t2.team_id
        LEFT JOIN Teams tw ON m.winner = tw.team_id
        WHERE t1.name = ? OR t2.name = ?
        ORDER BY m.date DESC LIMIT 20
    """, (formatted_name, formatted_name))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/series")
async def get_series_list():
    # Mock return for Series page
    return [
        {"id": "asian-games", "name": "Asian Games Qualifier 2026", "date": "May 2026"},
        {"id": "aus-pak", "name": "Australia tour of Pakistan 2026", "date": "May 2026"},
        {"id": "nz-ire", "name": "New Zealand tour of Ireland 2026", "date": "May 2026"}
    ]
    
@app.get("/api/league/{league_id}")
async def get_league_details(league_id: str):
    # Mock return for League page
    return {
        "id": league_id,
        "name": league_id.replace('-', ' ').title(),
        "status": "In Progress",
        "matches": []
    }

@app.get("/api/records/{format}")
async def get_format_records(format: str):
    conn = get_db()
    cursor = conn.cursor()
    format = format.upper()
    if format == 'ODI' or format == 'T20I' or format == 'TEST':
        fmt_query = format
    else:
        fmt_query = "All Formats"
        
    records = {}
    # Re-use global records logic but could filter by format if schema supported it. We'll just return global for now.
    cursor.execute("""
        SELECT p.name, c.bat_runs, c.matches, c.team_name 
        FROM PlayerCareerStats c JOIN Players p ON c.player_id = p.player_id
        ORDER BY c.bat_runs DESC LIMIT 10
    """)
    records["top_run_scorers"] = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return records

@app.post("/api/predict")
async def predict_match(req: PredictionRequest):
    if not model:
        return {"error": "AI Model is not loaded. Ensure models/advanced_predictor.pth exists."}
        
    # Simulate tensor translation for the requested teams
    # In reality, this would query the DB for the starting XI of each team
    # Sequence shape: (Batch Size=1, Seq Length=22, Feature Dim=15)
    sequence = torch.randn(1, 22, 15).to(device)
    
    with torch.no_grad():
        match_outcome, predicted_runs = model(sequence)
        
        # 0 = Team A wins, 1 = Team B wins
        outcome_prob = match_outcome.item()
        winner = req.team_b if outcome_prob > 0.5 else req.team_a
        win_probability = max(outcome_prob, 1 - outcome_prob) * 100
        
        runs = int(predicted_runs.item() * 100) # De-normalize
        
    return {
        "winner": winner,
        "win_probability": round(win_probability, 1),
        "top_batsman_runs": abs(runs)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.app:app", host="0.0.0.0", port=8000, reload=True)
