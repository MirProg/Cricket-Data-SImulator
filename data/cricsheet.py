import os
import urllib.request
import zipfile
import json
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def download_cricsheet_data():
    """Downloads and extracts the entire Cricsheet JSON database."""
    DATA_DIR = os.path.dirname(__file__)
    CRICSHEET_DIR = os.path.join(DATA_DIR, 'cricsheet')
    os.makedirs(CRICSHEET_DIR, exist_ok=True)
    
    zip_path = os.path.join(CRICSHEET_DIR, 't20s_json.zip')
    
    # We will fetch all_json.zip to grab every single historical match in the Cricsheet database
    url = "https://cricsheet.org/downloads/all_json.zip"
    
    if not os.path.exists(zip_path):
        logger.info(f"Downloading massive Cricsheet database from {url}...")
        try:
            urllib.request.urlretrieve(url, zip_path)
            logger.info("Download complete. Extracting JSON scorecards...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(CRICSHEET_DIR)
            logger.info("Extraction complete. Millions of historical balls ready for processing.")
        except Exception as e:
            logger.error(f"Failed to download Cricsheet data: {e}")
            return
    else:
        logger.info("Cricsheet database already downloaded.")

def process_cricsheet_scorecards():
    """Reads the Cricsheet JSON files and extracts player data and ball sequences."""
    DATA_DIR = os.path.dirname(__file__)
    CRICSHEET_DIR = os.path.join(DATA_DIR, 'cricsheet')
    
    if not os.path.exists(CRICSHEET_DIR):
        logger.error("Cricsheet directory not found.")
        return
        
    json_files = [f for f in os.listdir(CRICSHEET_DIR) if f.endswith('.json')]
    logger.info(f"Streaming {len(json_files)} historical scorecards into SQLite DB... This will take time.")
    
    from db import CricketDB
    db = CricketDB()
    
    # Process EVERY single match into SQL
    for count, file in enumerate(json_files):
        with open(os.path.join(CRICSHEET_DIR, file), 'r', encoding='utf-8') as f:
            match_data = json.load(f)
            
        info = match_data.get("info", {})
        cricinfo_id = file.replace('.json', '')
        
        # We assume the first element of 'teams' is team1 and second is team2
        teams = info.get("teams", ["Unknown1", "Unknown2"])
        team1 = teams[0] if len(teams) > 0 else "Unknown1"
        team2 = teams[1] if len(teams) > 1 else "Unknown2"
        
        sql_match = {
            "match_id": str(cricinfo_id),
            "date": info.get("dates", [""])[0],
            "venue": info.get("venue", ""),
            "city": info.get("city", ""),
            "format": info.get("match_type", ""),
            "gender": info.get("gender", ""),
            "team1": team1,
            "team2": team2,
            "winner": info.get("outcome", {}).get("winner", ""),
            "win_margin_runs": info.get("outcome", {}).get("by", {}).get("runs", 0),
            "win_margin_wickets": info.get("outcome", {}).get("by", {}).get("wickets", 0)
        }
        
        from orchestrator import register_match
        is_new = register_match(team1, team2, sql_match["date"], sql_match["format"], "cricsheet", cricinfo_id)
        
        if not is_new:
            continue
            
        # Parse innings and balls
        sql_balls = []
        innings_list = match_data.get("innings", [])
        for inn_idx, innings in enumerate(innings_list):
            if not isinstance(innings, dict):
                # Legacy cricsheet format fallback
                if isinstance(innings, list) and len(innings) > 0 and isinstance(innings[0], dict):
                    # old format {"1st innings": {"deliveries": [...]}}
                    for inn_key, inn_val in innings[0].items():
                        innings = inn_val
                else:
                    continue
                    
            overs = innings.get("overs", [])
            for over in overs:
                over_num = over.get("over", 0)
                for ball_idx, delivery in enumerate(over.get("deliveries", [])):
                    is_wicket = "wickets" in delivery
                    w_type = delivery["wickets"][0].get("kind", "") if is_wicket else ""
                    p_out = delivery["wickets"][0].get("player_out", "") if is_wicket else ""
                    
                    sql_balls.append((
                        str(cricinfo_id), inn_idx+1, over_num, ball_idx+1,
                        delivery.get("batter", ""), delivery.get("bowler", ""),
                        delivery.get("non_striker", ""),
                        delivery.get("runs", {}).get("batter", 0),
                        delivery.get("runs", {}).get("extras", 0),
                        is_wicket, w_type, p_out
                    ))
                        
        # Stream batch into SQLite
        db.insert_match_data(sql_match, sql_balls)
        
        if count > 0 and count % 500 == 0:
            logger.info(f"Streamed {count} scorecards into SQLite...")
            
    logger.info(f"Successfully streamed all Cricsheet matches into the SQL database.")


if __name__ == "__main__":
    download_cricsheet_data()
    process_cricsheet_scorecards()
