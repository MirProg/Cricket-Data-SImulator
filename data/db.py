import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

class CricketDB:
    def __init__(self, db_path=None):
        if not db_path:
            db_path = os.path.join(os.path.dirname(__file__), 'cricket_db.sqlite')
        self.db_path = db_path
        self._initialize_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_db(self):
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        if not os.path.exists(schema_path):
            logger.error("schema.sql not found!")
            return
            
        with open(schema_path, 'r') as f:
            schema_script = f.read()

        with self.get_connection() as conn:
            conn.executescript(schema_script)
            conn.commit()
            
    def insert_match_data(self, match_data, ball_data):
        """
        Batch inserts a match and all its balls to avoid 15,000 commits per match.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Insert Teams
            cursor.execute("INSERT OR IGNORE INTO Teams (team_id, name) VALUES (?, ?)", 
                           (match_data['team1'], match_data['team1']))
            cursor.execute("INSERT OR IGNORE INTO Teams (team_id, name) VALUES (?, ?)", 
                           (match_data['team2'], match_data['team2']))
                           
            # 2. Insert Match
            cursor.execute('''
                INSERT OR IGNORE INTO Matches 
                (match_id, date, venue, city, format, gender, team1_id, team2_id, winner, win_margin_runs, win_margin_wickets)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                match_data['match_id'], match_data.get('date'), match_data.get('venue'),
                match_data.get('city'), match_data.get('format'), match_data.get('gender'),
                match_data['team1'], match_data['team2'], match_data.get('winner'),
                match_data.get('win_margin_runs', 0), match_data.get('win_margin_wickets', 0)
            ))
            
            # 3. Insert Balls (Batch)
            if ball_data:
                cursor.executemany('''
                    INSERT INTO BallByBall 
                    (match_id, innings_number, over_num, ball_num, batter_id, bowler_id, non_striker_id, runs_batter, runs_extras, is_wicket, wicket_type, player_out_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', ball_data)
                
            conn.commit()
