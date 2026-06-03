import sqlite3

DB_PATH = r"C:\Users\seo\.local\bin\cricket_simulator\data\master_archive.sqlite"

def build_schema():
    print("Building Ultimate Cricket Database Schema...")
    with sqlite3.connect(DB_PATH) as conn:
        # Core Hierarchy
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS Seasons (
                season_id TEXT PRIMARY KEY,
                name TEXT
            );
            
            CREATE TABLE IF NOT EXISTS Series (
                series_id TEXT PRIMARY KEY,
                season_id TEXT,
                name TEXT,
                type TEXT,
                FOREIGN KEY(season_id) REFERENCES Seasons(season_id)
            );
            
            CREATE TABLE IF NOT EXISTS Matches (
                match_id TEXT PRIMARY KEY,
                series_id TEXT,
                ground_id TEXT,
                team1_id TEXT,
                team2_id TEXT,
                date_start DATETIME,
                date_end DATETIME,
                format_id TEXT,
                toss_winner_id TEXT,
                toss_decision TEXT,
                match_status TEXT,
                result_type TEXT,
                win_margin_runs INTEGER,
                win_margin_wickets INTEGER,
                player_of_match_id TEXT,
                FOREIGN KEY(series_id) REFERENCES Series(series_id)
            );
        """)
        
        # 4-Innings Architecture
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS Innings (
                innings_id TEXT PRIMARY KEY,
                match_id TEXT,
                innings_number INTEGER,
                batting_team_id TEXT,
                bowling_team_id TEXT,
                total_runs INTEGER,
                total_wickets INTEGER,
                total_overs REAL,
                declared BOOLEAN,
                extras_b INTEGER,
                extras_lb INTEGER,
                extras_w INTEGER,
                extras_nb INTEGER,
                FOREIGN KEY(match_id) REFERENCES Matches(match_id)
            );
        """)
        
        # Scorecards
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS Batting_Scorecards (
                batting_id TEXT PRIMARY KEY,
                innings_id TEXT,
                player_id TEXT,
                position INTEGER,
                runs INTEGER,
                balls_faced INTEGER,
                fours INTEGER,
                sixes INTEGER,
                minutes_batted INTEGER,
                dismissal_type_id TEXT,
                bowler_id TEXT,
                fielder_id TEXT,
                FOREIGN KEY(innings_id) REFERENCES Innings(innings_id)
            );
            
            CREATE TABLE IF NOT EXISTS Bowling_Scorecards (
                bowling_id TEXT PRIMARY KEY,
                innings_id TEXT,
                player_id TEXT,
                overs REAL,
                maidens INTEGER,
                runs_conceded INTEGER,
                wickets INTEGER,
                wides INTEGER,
                no_balls INTEGER,
                FOREIGN KEY(innings_id) REFERENCES Innings(innings_id)
            );
        """)
        
        print("Schema successfully built in master_archive.sqlite.")

if __name__ == "__main__":
    build_schema()
