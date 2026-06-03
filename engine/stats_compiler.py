import sqlite3
import json
import os

DB_PATH = "D:/cricket_data/cricmatrix.db"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "player_stats.json")

def compile_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("Compiling batting stats...")
    c.execute("""
        SELECT batter, 
               SUM(runs_batter) as total_runs, 
               COUNT(ball) as total_balls, 
               SUM(is_wicket) as outs 
        FROM deliveries 
        GROUP BY batter 
        HAVING total_balls >= 30
    """)
    batting_data = c.fetchall()
    
    print("Compiling bowling stats...")
    c.execute("""
        SELECT bowler, 
               SUM(runs_total) as runs_conceded, 
               COUNT(ball) as balls_bowled, 
               SUM(is_wicket) as wickets_taken 
        FROM deliveries 
        GROUP BY bowler 
        HAVING balls_bowled >= 30
    """)
    bowling_data = c.fetchall()
    
    conn.close()
    
    stats = {}
    
    # Process Batting
    for row in batting_data:
        name, runs, balls, outs = row
        avg = runs / outs if outs > 0 else runs if runs > 0 else 10.0
        sr = (runs / balls) * 100 if balls > 0 else 100.0
        
        stats[name] = {
            "batting_avg": round(avg, 2),
            "batting_sr": round(sr, 2),
            "batting_runs": runs,
            "batting_balls": balls
        }
        
    # Process Bowling
    for row in bowling_data:
        name, runs_c, balls_b, wkts = row
        econ = (runs_c / balls_b) * 6 if balls_b > 0 else 8.0
        sr = balls_b / wkts if wkts > 0 else balls_b if balls_b > 0 else 24.0
        avg = runs_c / wkts if wkts > 0 else runs_c if runs_c > 0 else 30.0
        
        if name not in stats:
            stats[name] = {}
            
        stats[name].update({
            "bowling_econ": round(econ, 2),
            "bowling_sr": round(sr, 2),
            "bowling_avg": round(avg, 2),
            "bowling_balls": balls_b,
            "bowling_wickets": wkts
        })
        
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(stats, f, indent=2)
        
    print(f"Successfully compiled stats for {len(stats)} players to {OUTPUT_PATH}")

if __name__ == "__main__":
    compile_stats()
