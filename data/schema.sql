CREATE TABLE IF NOT EXISTS Teams (
    team_id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Players (
    player_id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Matches (
    match_id TEXT PRIMARY KEY,
    date TEXT,
    venue TEXT,
    city TEXT,
    format TEXT,
    gender TEXT,
    team1_id TEXT,
    team2_id TEXT,
    winner TEXT,
    win_margin_runs INTEGER,
    win_margin_wickets INTEGER,
    FOREIGN KEY(team1_id) REFERENCES Teams(team_id),
    FOREIGN KEY(team2_id) REFERENCES Teams(team_id)
);

CREATE TABLE IF NOT EXISTS Innings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id TEXT,
    innings_number INTEGER,
    batting_team_id TEXT,
    bowling_team_id TEXT,
    total_runs INTEGER DEFAULT 0,
    total_wickets INTEGER DEFAULT 0,
    FOREIGN KEY(match_id) REFERENCES Matches(match_id)
);

CREATE TABLE IF NOT EXISTS BallByBall (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id TEXT,
    innings_number INTEGER,
    over_num INTEGER,
    ball_num INTEGER,
    batter_id TEXT,
    bowler_id TEXT,
    non_striker_id TEXT,
    runs_batter INTEGER DEFAULT 0,
    runs_extras INTEGER DEFAULT 0,
    is_wicket BOOLEAN DEFAULT 0,
    wicket_type TEXT,
    player_out_id TEXT,
    FOREIGN KEY(match_id) REFERENCES Matches(match_id)
);

-- Indexes for API performance
CREATE INDEX IF NOT EXISTS idx_bbb_match_id ON BallByBall(match_id);
CREATE INDEX IF NOT EXISTS idx_innings_match_id ON Innings(match_id);
CREATE INDEX IF NOT EXISTS idx_matches_date ON Matches(date);
