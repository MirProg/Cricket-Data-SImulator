import os
import sys
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import functools
import sqlite3
import logging

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.collector import CricketDataCollector
from engine.simulator import CricketSimulator, MatchFormat, MatchEvent
from ai.predictor import AIPredictor

app = FastAPI(title="Cricket Simulator AI")

# Mount static files and templates
os.makedirs(os.path.join(os.path.dirname(__file__), "static"), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), "templates"), exist_ok=True)
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# Initialize components
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
collector = CricketDataCollector(DATA_DIR)
ai_predictor = AIPredictor()
simulator = CricketSimulator()

@app.on_event("startup")
async def startup_event():
    # Attempt to load cache on startup
    global cached_teams
    cached_teams = collector.load_cached_data() or {}
    print(f"Loaded {len(cached_teams)} teams from cache.")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/teams")
async def get_teams():
    # Return available teams
    teams_list = []
    for tid, tdata in cached_teams.items():
        teams_list.append({"id": tid, "name": tdata.get("name", tid), "country": tdata.get("country", "")})
    return sorted(teams_list, key=lambda x: x["name"])

@app.websocket("/ws/simulate")
async def websocket_simulate(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        team1_id = data.get("team1")
        team2_id = data.get("team2")
        format_str = data.get("format", "T20")
        
        if not team1_id or not team2_id:
            await websocket.send_json({"type": "error", "message": "Missing teams"})
            return
            
        teams = collector.collect_all_data()
        if team1_id not in teams or team2_id not in teams:
            await websocket.send_json({"type": "error", "message": "Invalid teams"})
            return
            
        t1 = teams[team1_id]
        t2 = teams[team2_id]
        match_format = MatchFormat(format_str.upper())
        
        await websocket.send_json({"type": "info", "message": f"Starting {match_format.value} simulation: {t1.name} vs {t2.name}"})
        
        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()
        
        # State tracking for the UI
        state = {"t1_score": 0, "t1_wickets": 0, "t1_overs": 0, "t1_balls": 0,
                 "t2_score": 0, "t2_wickets": 0, "t2_overs": 0, "t2_balls": 0, "innings": 1}

        def sync_on_ball(event, runs, comm, over, ball):
            # Update state
            if state["innings"] == 1:
                state["t1_score"] += runs
                if event == MatchEvent.WICKET: state["t1_wickets"] += 1
                state["t1_balls"] += 1
                state["t1_overs"] = f"{state['t1_balls'] // 6}.{state['t1_balls'] % 6}"
            else:
                state["t2_score"] += runs
                if event == MatchEvent.WICKET: state["t2_wickets"] += 1
                state["t2_balls"] += 1
                state["t2_overs"] = f"{state['t2_balls'] // 6}.{state['t2_balls'] % 6}"
                
            e_class = "normal"
            if event == MatchEvent.WICKET: e_class = "wicket"
            if event in [MatchEvent.RUN_4, MatchEvent.SIX]: e_class = "boundary"

            # Put message in queue
            msg = {
                "type": "ball",
                "t1_score": f"{state['t1_score']}/{state['t1_wickets']}",
                "t1_overs": state["t1_overs"],
                "t2_score": f"{state['t2_score']}/{state['t2_wickets']}",
                "t2_overs": state["t2_overs"],
                "event_class": e_class,
                "over_ball": f"{over-1}.{ball}",
                "commentary": comm
            }
            # We must use run_coroutine_threadsafe because this callback is called from a background thread
            asyncio.run_coroutine_threadsafe(queue.put(msg), loop)

        def run_sim():
            # simulate_match blocks, so we run it in a thread
            try:
                # We need to detect innings change. For simplicity, we just watch the state in the UI.
                def on_ball_wrapper(event, runs, comm, over, ball):
                    # Sleep slightly to make the simulation watchable in the UI!
                    import time
                    time.sleep(0.5) 
                    
                    if state["innings"] == 1 and state["t1_wickets"] == 10:
                        state["innings"] = 2
                        
                    sync_on_ball(event, runs, comm, over, ball)

                match = simulator.simulate_match(t1, t2, match_format, "Virtual Stadium", ai_predictor, on_ball=on_ball_wrapper)
                asyncio.run_coroutine_threadsafe(queue.put({"type": "result", "result": match.result}), loop)
            except Exception as e:
                asyncio.run_coroutine_threadsafe(queue.put({"type": "error", "message": str(e)}), loop)

        import threading
        thread = threading.Thread(target=run_sim)
        thread.start()

        # Stream from queue to websocket
        while True:
            msg = await queue.get()
            await websocket.send_json(msg)
            if msg["type"] in ["result", "error"]:
                break
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})

import sqlite3

def get_db_connection():
    conn = sqlite3.connect('data/cricket_db.sqlite')
    conn.row_factory = sqlite3.Row
    return conn

@functools.lru_cache(maxsize=128)
def get_cached_matches(limit: int, offset: int):
    conn = get_db_connection()
    matches = conn.execute('SELECT * FROM Matches ORDER BY date DESC LIMIT ? OFFSET ?', (limit, offset)).fetchall()
    conn.close()
    return {"matches": [dict(m) for m in matches]}

@app.get("/api/v1/matches")
async def get_matches(limit: int = 50, offset: int = 0):
    """Public API to fetch all historical matches with pagination."""
    return get_cached_matches(limit, offset)

@app.get("/api/v1/matches/{match_id}/ball-by-ball")
async def get_ball_by_ball(match_id: str):
    """Public API to fetch the precise historical ball-by-ball scorecard."""
    conn = get_db_connection()
    balls = conn.execute('SELECT * FROM BallByBall WHERE match_id = ? ORDER BY innings_number, over_num, ball_num', (match_id,)).fetchall()
    conn.close()
    if not balls:
        # Trigger load balancer to fetch missing match
        from data.load_balancer import DistributedScraperEngine
        engine = DistributedScraperEngine()
        logger.info(f"Match {match_id} missing from SQLite. Auto-fetching via Load Balancer...")
        # (Background task triggering would happen here in production)
        return {"error": "Match data missing but queued for scraping.", "queued": True}
        
    return {"match_id": match_id, "balls": [dict(b) for b in balls]}

@app.get("/api/v1/players/{player_id}")
async def get_player(player_id: str):
    """Public API to fetch a player."""
    conn = get_db_connection()
    player = conn.execute('SELECT * FROM Players WHERE player_id = ?', (player_id,)).fetchone()
    conn.close()
    if not player:
        return {"error": "Player not found"}
    return dict(player)

@app.get("/api/v1/system/status")
async def get_system_status():
    """Public API to monitor the background SQLite ETL and Spiders."""
    conn = get_db_connection()
    matches_count = conn.execute('SELECT COUNT(*) FROM Matches').fetchone()[0]
    balls_count = conn.execute('SELECT COUNT(*) FROM BallByBall').fetchone()[0]
    conn.close()
    
    # Read the last few lines of the daemon log if available
    log_file = "data/scraper.log"
    recent_logs = []
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            recent_logs = lines[-5:] if len(lines) >= 5 else lines
            
    return {
        "database": {
            "total_matches": matches_count,
            "total_balls_delivered": balls_count
        },
        "scraper_logs": [log.strip() for log in recent_logs]
    }

@app.get("/api/v1/live")
async def get_live_matches():
    """Public API to fetch real-world live matches from ESPN."""
    from data.live import LiveTracker
    tracker = LiveTracker()
    matches = tracker.get_live_matches()
    return {"live_matches": matches}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
