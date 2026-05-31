import sqlite3
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - STATS_BUILDER - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def overs_to_balls(overs):
    if not overs:
        return 0
    # overs can be a float or string, e.g. 10.3 or "10.3"
    try:
        parts = str(overs).split('.')
        ovs = int(parts[0])
        balls = int(parts[1]) if len(parts) > 1 else 0
        # safety check for formatting like 10.5
        if balls >= 6:
            # Handle cases like "10.6" -> 11 overs or handle it gracefully
            return ovs * 6 + (balls % 6)
        return ovs * 6 + balls
    except (ValueError, IndexError):
        return 0

def balls_to_overs(balls):
    if not balls:
        return 0.0
    ovs = balls // 6
    bls = balls % 6
    return float(f"{ovs}.{bls}")

def rebuild_career_stats(db_path='data/cricket_db.sqlite'):
    logger.info(f"Connecting to database {db_path} to rebuild career stats...")
    conn = sqlite3.connect(db_path, timeout=60.0)
    
    # Initialize database tables if they do not exist yet
    import os
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    if os.path.exists(schema_path):
        with open(schema_path, 'r', encoding='utf-8') as sf:
            conn.executescript(sf.read())
        conn.commit()
        
    cursor = conn.cursor()
    
    # 1. Clear existing stats
    cursor.execute("DELETE FROM PlayerCareerStats")
    conn.commit()
    
    # We will compute player career stats in memory to be fast and handle edge cases cleanly
    # Structure: stats[(player_id, format)] = dict
    stats = defaultdict(lambda: {
        'matches': 0,
        'bat_innings': 0,
        'bat_runs': 0,
        'highest_score': 0,
        'highest_score_not_out': False,
        'fifties': 0,
        'hundreds': 0,
        'fours': 0,
        'sixes': 0,
        'not_outs': 0,
        'total_balls_faced': 0,
        'bowl_innings': 0,
        'total_balls_bowled': 0,
        'bowl_maidens': 0,
        'bowl_runs': 0,
        'bowl_wickets': 0,
        'five_wickets': 0,
        'best_bowling_runs': None,
        'best_bowling_wickets': -1
    })
    
    # 2. Process Batting scorecards (which also represent match participation in playing XI)
    logger.info("Aggregating batting stats and matches played...")
    cursor.execute('''
        SELECT 
            pb.player_id, 
            m.format, 
            pb.dismissal_text, 
            pb.runs, 
            pb.balls, 
            pb.fours, 
            pb.sixes
        FROM CAPlayerBattingScorecard pb
        JOIN CAInnings i ON pb.innings_id = i.id
        JOIN CAMatches m ON i.match_id = m.match_id
    ''')
    
    batting_rows = cursor.fetchall()
    for row in batting_rows:
        pid, fmt, dismissal, runs, balls, fours, sixes = row
        if not pid or not fmt:
            continue
            
        p_stats = stats[(pid, fmt)]
        
        # Every scorecard entry is a match played
        p_stats['matches'] += 1
        
        if dismissal != 'did not bat':
            p_stats['bat_innings'] += 1
            p_stats['bat_runs'] += runs
            p_stats['total_balls_faced'] += balls
            p_stats['fours'] += fours
            p_stats['sixes'] += sixes
            
            # Not outs
            is_not_out = False
            if 'not out' in dismissal.lower():
                p_stats['not_outs'] += 1
                is_not_out = True
                
            # Highest score
            if runs > p_stats['highest_score']:
                p_stats['highest_score'] = runs
                p_stats['highest_score_not_out'] = is_not_out
            elif runs == p_stats['highest_score'] and is_not_out and not p_stats['highest_score_not_out']:
                # Equal highest score, prefer not out
                p_stats['highest_score_not_out'] = True
                
            # Milestones
            if runs >= 100:
                p_stats['hundreds'] += 1
            elif runs >= 50:
                p_stats['fifties'] += 1
                
    # 3. Process Bowling scorecards
    logger.info("Aggregating bowling stats...")
    cursor.execute('''
        SELECT 
            pb.player_id, 
            m.format, 
            pb.overs, 
            pb.maidens, 
            pb.runs, 
            pb.wickets
        FROM CAPlayerBowlingScorecard pb
        JOIN CAInnings i ON pb.innings_id = i.id
        JOIN CAMatches m ON i.match_id = m.match_id
    ''')
    
    bowling_rows = cursor.fetchall()
    for row in bowling_rows:
        pid, fmt, overs, maidens, runs, wickets = row
        if not pid or not fmt:
            continue
            
        p_stats = stats[(pid, fmt)]
        
        p_stats['bowl_innings'] += 1
        p_stats['total_balls_bowled'] += overs_to_balls(overs)
        p_stats['bowl_maidens'] += maidens
        p_stats['bowl_runs'] += runs
        p_stats['bowl_wickets'] += wickets
        
        if wickets >= 5:
            p_stats['five_wickets'] += 1
            
        # Check Best Bowling Figures (BBI)
        # We prefer most wickets, then least runs
        is_best = False
        if wickets > p_stats['best_bowling_wickets']:
            is_best = True
        elif wickets == p_stats['best_bowling_wickets']:
            if p_stats['best_bowling_runs'] is None or runs < p_stats['best_bowling_runs']:
                is_best = True
                
        if is_best:
            p_stats['best_bowling_wickets'] = wickets
            p_stats['best_bowling_runs'] = runs

    # 4. Insert computed stats into the database in bulk
    logger.info(f"Saving career stats for {len(stats)} player-format combinations...")
    
    insert_data = []
    for (pid, fmt), p_stats in stats.items():
        # Compute averages, strike rates, economy
        bat_avg = None
        if p_stats['bat_innings'] > 0:
            outs = p_stats['bat_innings'] - p_stats['not_outs']
            if outs > 0:
                bat_avg = round(p_stats['bat_runs'] / outs, 2)
            else:
                bat_avg = float(p_stats['bat_runs']) # remain undefined or set to runs if never got out
                
        bat_sr = None
        if p_stats['total_balls_faced'] > 0:
            bat_sr = round((p_stats['bat_runs'] * 100.0) / p_stats['total_balls_faced'], 2)
            
        bowl_avg = None
        if p_stats['bowl_wickets'] > 0:
            bowl_avg = round(p_stats['bowl_runs'] / p_stats['bowl_wickets'], 2)
            
        bowl_econ = None
        if p_stats['total_balls_bowled'] > 0:
            bowl_econ = round((p_stats['bowl_runs'] * 6.0) / p_stats['total_balls_bowled'], 2)
            
        bowl_sr = None
        if p_stats['bowl_wickets'] > 0:
            bowl_sr = round(p_stats['total_balls_bowled'] / p_stats['bowl_wickets'], 2)
            
        bowl_overs = balls_to_overs(p_stats['total_balls_bowled'])
        best_runs = p_stats['best_bowling_runs'] if p_stats['best_bowling_wickets'] >= 0 else None
        best_wickets = p_stats['best_bowling_wickets'] if p_stats['best_bowling_wickets'] >= 0 else None
        
        insert_data.append((
            pid, fmt, p_stats['matches'],
            p_stats['bat_innings'], p_stats['bat_runs'], bat_avg, bat_sr,
            p_stats['highest_score'], p_stats['highest_score_not_out'],
            p_stats['fifties'], p_stats['hundreds'], p_stats['fours'], p_stats['sixes'], p_stats['not_outs'],
            p_stats['bowl_innings'], bowl_overs, p_stats['bowl_maidens'], p_stats['bowl_runs'], p_stats['bowl_wickets'],
            bowl_avg, bowl_econ, bowl_sr, p_stats['five_wickets'], best_runs, best_wickets
        ))
        
    cursor.executemany('''
        INSERT INTO PlayerCareerStats (
            player_id, format, matches,
            bat_innings, bat_runs, bat_avg, bat_sr,
            highest_score, highest_score_not_out,
            fifties, hundreds, fours, sixes, not_outs,
            bowl_innings, bowl_overs, bowl_maidens, bowl_runs, bowl_wickets,
            bowl_avg, bowl_econ, bowl_sr, five_wickets, best_bowling_runs, best_bowling_wickets
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', insert_data)
    
    conn.commit()
    conn.close()
    logger.info("Career stats database update complete!")

if __name__ == '__main__':
    rebuild_career_stats()
