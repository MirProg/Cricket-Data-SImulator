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


-- ==========================================
-- CricketArchive Scorecard Parser Tables (CA)
-- ==========================================

CREATE TABLE IF NOT EXISTS CATournaments (
    tournament_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT
);

CREATE TABLE IF NOT EXISTS CATeams (
    team_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT
);

CREATE TABLE IF NOT EXISTS CAPlayers (
    player_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    dob TEXT,
    url TEXT
);

CREATE TABLE IF NOT EXISTS CAMatches (
    match_id TEXT PRIMARY KEY,
    title TEXT,
    tournament_id TEXT,
    date TEXT,
    venue TEXT,
    ground_id TEXT,
    format TEXT,
    team1_id TEXT,
    team2_id TEXT,
    toss_winner_id TEXT,
    toss_decision TEXT,
    result TEXT,
    win_margin_runs INTEGER,
    win_margin_wickets INTEGER,
    win_margin_text TEXT,
    umpire1_id TEXT,
    umpire2_id TEXT,
    tv_umpire_id TEXT,
    referee_id TEXT,
    reserve_umpire_id TEXT,
    player_of_match_id TEXT,
    points TEXT,
    FOREIGN KEY(tournament_id) REFERENCES CATournaments(tournament_id),
    FOREIGN KEY(team1_id) REFERENCES CATeams(team_id),
    FOREIGN KEY(team2_id) REFERENCES CATeams(team_id)
);

-- Innings totals
CREATE TABLE IF NOT EXISTS CAInnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id TEXT,
    innings_number INTEGER,
    batting_team_id TEXT,
    bowling_team_id TEXT,
    runs INTEGER DEFAULT 0,
    wickets INTEGER DEFAULT 0,
    overs TEXT,
    extras_b INTEGER DEFAULT 0,
    extras_lb INTEGER DEFAULT 0,
    extras_nb INTEGER DEFAULT 0,
    extras_wd INTEGER DEFAULT 0,
    extras_total INTEGER DEFAULT 0,
    FOREIGN KEY(match_id) REFERENCES CAMatches(match_id),
    FOREIGN KEY(batting_team_id) REFERENCES CATeams(team_id),
    FOREIGN KEY(bowling_team_id) REFERENCES CATeams(team_id)
);

-- Batting scorecard entries
CREATE TABLE IF NOT EXISTS CAPlayerBattingScorecard (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    innings_id INTEGER,
    player_id TEXT,
    dismissal_text TEXT,
    runs INTEGER DEFAULT 0,
    balls INTEGER DEFAULT 0,
    mins INTEGER,
    fours INTEGER DEFAULT 0,
    sixes INTEGER DEFAULT 0,
    dots INTEGER DEFAULT 0,
    strike_rate REAL,
    FOREIGN KEY(innings_id) REFERENCES CAInnings(id),
    FOREIGN KEY(player_id) REFERENCES CAPlayers(player_id)
);

-- Bowling scorecard entries
CREATE TABLE IF NOT EXISTS CAPlayerBowlingScorecard (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    innings_id INTEGER,
    player_id TEXT,
    overs REAL,
    maidens INTEGER DEFAULT 0,
    runs INTEGER DEFAULT 0,
    wickets INTEGER DEFAULT 0,
    wides INTEGER DEFAULT 0,
    no_balls INTEGER DEFAULT 0,
    dots INTEGER DEFAULT 0,
    fours INTEGER DEFAULT 0,
    sixes INTEGER DEFAULT 0,
    econ REAL,
    FOREIGN KEY(innings_id) REFERENCES CAInnings(id),
    FOREIGN KEY(player_id) REFERENCES CAPlayers(player_id)
);

-- Fall of Wickets
CREATE TABLE IF NOT EXISTS CAFallOfWickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    innings_id INTEGER,
    wicket_num INTEGER,
    score INTEGER,
    player_out_id TEXT,
    overs REAL,
    FOREIGN KEY(innings_id) REFERENCES CAInnings(id),
    FOREIGN KEY(player_out_id) REFERENCES CAPlayers(player_id)
);

-- Match Footnotes / Notes
CREATE TABLE IF NOT EXISTS CAMatchNotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id TEXT,
    note_text TEXT,
    FOREIGN KEY(match_id) REFERENCES CAMatches(match_id)
);

-- Precalculated Player Career Statistics
CREATE TABLE IF NOT EXISTS PlayerCareerStats (
    player_id TEXT,
    format TEXT,
    matches INTEGER DEFAULT 0,
    
    -- Batting Stats
    bat_innings INTEGER DEFAULT 0,
    bat_runs INTEGER DEFAULT 0,
    bat_avg REAL,
    bat_sr REAL,
    highest_score INTEGER DEFAULT 0,
    highest_score_not_out BOOLEAN DEFAULT 0,
    fifties INTEGER DEFAULT 0,
    hundreds INTEGER DEFAULT 0,
    fours INTEGER DEFAULT 0,
    sixes INTEGER DEFAULT 0,
    not_outs INTEGER DEFAULT 0,
    
    -- Bowling Stats
    bowl_innings INTEGER DEFAULT 0,
    bowl_overs REAL DEFAULT 0.0,
    bowl_maidens INTEGER DEFAULT 0,
    bowl_runs INTEGER DEFAULT 0,
    bowl_wickets INTEGER DEFAULT 0,
    bowl_avg REAL,
    bowl_econ REAL,
    bowl_sr REAL,
    five_wickets INTEGER DEFAULT 0,
    best_bowling_runs INTEGER,
    best_bowling_wickets INTEGER,
    
    PRIMARY KEY (player_id, format),
    FOREIGN KEY(player_id) REFERENCES CAPlayers(player_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_cainnings_match ON CAInnings(match_id);
CREATE INDEX IF NOT EXISTS idx_cabatting_innings ON CAPlayerBattingScorecard(innings_id);
CREATE INDEX IF NOT EXISTS idx_cabatting_player ON CAPlayerBattingScorecard(player_id);
CREATE INDEX IF NOT EXISTS idx_cabowling_innings ON CAPlayerBowlingScorecard(innings_id);
CREATE INDEX IF NOT EXISTS idx_cabowling_player ON CAPlayerBowlingScorecard(player_id);
CREATE INDEX IF NOT EXISTS idx_cafow_innings ON CAFallOfWickets(innings_id);
CREATE INDEX IF NOT EXISTS idx_camatchnotes_match ON CAMatchNotes(match_id);
CREATE INDEX IF NOT EXISTS idx_camatches_date ON CAMatches(date);
CREATE INDEX IF NOT EXISTS idx_camatches_tournament ON CAMatches(tournament_id);
