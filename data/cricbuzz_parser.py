import json
import logging
import sqlite3
import requests
import time
from bs4 import BeautifulSoup
from orchestrator import register_match
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - CRICBUZZ - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = 'data/cricket_db.sqlite'
JSONL_PATH = 'data/cricbuzz_history_db.jsonl'

def parse_cricbuzz():
    logger.info("Starting Deep Cricbuzz Parser...")
    
    # Load all 94k matches
    matches = []
    with open(JSONL_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                matches.append(json.loads(line))
            except:
                pass
                
    logger.info(f"Loaded {len(matches)} Cricbuzz metadata records.")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Process matches
    for i, match in enumerate(matches):
        match_id = match.get('match_id') or match.get('id')
        if not match_id:
            continue
        title = match.get('title', '')
        
        # Simple extraction from title: KKR vs RCB, 4th match...
        parts = title.replace('Cricket scorecard | ', '').split(', ')
        teams_part = parts[0]
        if ' vs ' in teams_part:
            team1, team2 = teams_part.split(' vs ')
        else:
            continue
            
        # Register to deduplicate
        is_new = register_match(team1.strip(), team2.strip(), "2026-05-31", "T20", "cricbuzz", match_id)
        if not is_new:
            continue
            
        logger.info(f"Scraping new match: {team1} vs {team2} (ID: {match_id})")
        # In a full implementation, we fetch the HTML here and parse the DOM.
        # Since Cricbuzz structure is complex, we will implement the DOM parsing in Phase 2.
        
        if i > 0 and i % 100 == 0:
            logger.info(f"Processed {i} Cricbuzz matches...")
            time.sleep(1)

if __name__ == "__main__":
    parse_cricbuzz()
