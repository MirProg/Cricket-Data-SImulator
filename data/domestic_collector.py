import os
import sys
import logging
sys.path.insert(0, os.path.dirname(__file__))
from collector import CricketDataCollector

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def fetch_domestic_leagues():
    DATA_DIR = os.path.dirname(__file__)
    collector = CricketDataCollector(DATA_DIR)
    
    domestic_classes = {
        "First-Class": 4,
        "List A": 5,
        "Domestic T20": 6
    }
    
    all_domestic_players = {}
    
    for format_name, class_id in domestic_classes.items():
        logger.info(f"Fetching local teams & players for {format_name}...")
        
        # Scrape batting
        bat_data_list = collector._scrape_all_pages(class_id, "batting", f"{format_name} Batting")
        # Scrape bowling
        bowl_data_list = collector._scrape_all_pages(class_id, "bowling", f"{format_name} Bowling")
        
        for stats in bat_data_list:
            p_id = str(stats["player_id"])
            if p_id not in all_domestic_players:
                all_domestic_players[p_id] = {"name": stats["name"], "team": stats.get("team", "Unknown"), "formats": {}}
            all_domestic_players[p_id]["formats"][format_name] = {"batting": stats}
            
        for stats in bowl_data_list:
            p_id = str(stats["player_id"])
            if p_id not in all_domestic_players:
                all_domestic_players[p_id] = {"name": stats["name"], "team": stats.get("team", "Unknown"), "formats": {}}
            if format_name not in all_domestic_players[p_id]["formats"]:
                all_domestic_players[p_id]["formats"][format_name] = {}
            all_domestic_players[p_id]["formats"][format_name]["bowling"] = stats
            
    # Process into teams
    domestic_teams = {}
    for p_id, p_data in all_domestic_players.items():
        t_name = p_data["team"]
        if t_name not in domestic_teams:
            domestic_teams[t_name] = {
                "name": t_name,
                "country": "Domestic",
                "players": {}
            }
            
        bat_stats = list(p_data["formats"].values())[0].get("batting", {})
        bowl_stats = list(p_data["formats"].values())[0].get("bowling", {})
        
        player_dict = {
            "name": p_data["name"],
            "role": "ALL_ROUNDER",
            "batting_avg": float(bat_stats.get("bat_avg", 10.0)),
            "batting_sr": float(bat_stats.get("bat_sr", 80.0)),
            "highest_score": int(bat_stats.get("hs", 0)),
            "bowling_avg": float(bowl_stats.get("bowl_avg", 40.0)),
            "economy": float(bowl_stats.get("econ", 6.0)),
            "wickets": int(bowl_stats.get("wickets", 0)),
            "recent_form": 1.0
        }
        domestic_teams[t_name]["players"][p_id] = player_dict
        
    logger.info(f"Successfully fetched {len(domestic_teams)} domestic state/franchise teams!")
    
    # Load existing teams, merge, and save
    existing_teams = collector.load_cached_data() or {}
    existing_teams.update(domestic_teams)
    
    collector._cache_data(existing_teams)
    logger.info("Domestic database successfully integrated into the main database.")

if __name__ == "__main__":
    fetch_domestic_leagues()
