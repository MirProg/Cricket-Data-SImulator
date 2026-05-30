"""
Data models for the cricket simulator.
Defines classes for Team, Player, Match, and related entities.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import json


class MatchFormat(Enum):
    TEST = "Test"
    ODI = "ODI"
    T20 = "T20"


class PlayerRole(Enum):
    BATSMAN = "Batsman"
    BOWLER = "Bowler"
    ALLROUNDER = "Allrounder"
    WICKETKEEPER = "Wicketkeeper"


@dataclass
class Player:
    """Represents a cricket player with statistical attributes."""
    player_id: str
    name: str
    team: str
    role: PlayerRole
    batting_avg: float = 0.0
    batting_sr: float = 0.0  # Strike rate
    bowling_avg: float = 99.0  # High value for non-bowlers
    bowling_sr: float = 0.0    # Strike rate (balls per wicket)
    economy: float = 5.0       # Runs per over
    recent_form: float = 0.5   # 0-1 scale, 0.5 is average
    experience: int = 0        # Number of matches played
    is_captain: bool = False
    is_wicketkeeper: bool = False

    def to_dict(self) -> Dict:
        """Convert player to dictionary for serialization."""
        return {
            "player_id": self.player_id,
            "name": self.name,
            "team": self.team,
            "role": self.role.value,
            "batting_avg": self.batting_avg,
            "batting_sr": self.batting_sr,
            "bowling_avg": self.bowling_avg,
            "bowling_sr": self.bowling_sr,
            "economy": self.economy,
            "recent_form": self.recent_form,
            "experience": self.experience,
            "is_captain": self.is_captain,
            "is_wicketkeeper": self.is_wicketkeeper
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Player':
        """Create Player from dictionary."""
        return cls(
            player_id=data["player_id"],
            name=data["name"],
            team=data["team"],
            role=PlayerRole(data["role"]),
            batting_avg=data.get("batting_avg", 0.0),
            batting_sr=data.get("batting_sr", 0.0),
            bowling_avg=data.get("bowling_avg", 99.0),
            bowling_sr=data.get("bowling_sr", 0.0),
            economy=data.get("economy", 5.0),
            recent_form=data.get("recent_form", 0.5),
            experience=data.get("experience", 0),
            is_captain=data.get("is_captain", False),
            is_wicketkeeper=data.get("is_wicketkeeper", False)
        )


@dataclass
class Team:
    """Represents a cricket team with players and team statistics."""
    team_id: str
    name: str
    country: str
    format_rankings: Dict[MatchFormat, int] = field(default_factory=dict)
    players: List[Player] = field(default_factory=list)
    home_advantage: float = 0.0

    def get_playing_xi(self) -> List[Player]:
        """Get the best playing XI based on form and role balance."""
        # Simple implementation: sort by recent form and pick top XI
        # In reality, this would consider captain's choice, pitch conditions, etc.
        sorted_players = sorted(self.players, key=lambda p: p.recent_form, reverse=True)
        return sorted_players[:11]

    def get_batters(self) -> List[Player]:
        """Get batsmen from the team."""
        return [p for p in self.players if p.role in [PlayerRole.BATSMAN, PlayerRole.ALLROUNDER, PlayerRole.WICKETKEEPER]]

    def get_bowlers(self) -> List[Player]:
        """Get bowlers from the team."""
        return [p for p in self.players if p.role in [PlayerRole.BOWLER, PlayerRole.ALLROUNDER]]

    def to_dict(self) -> Dict:
        """Convert team to dictionary for serialization."""
        return {
            "team_id": self.team_id,
            "name": self.name,
            "country": self.country,
            "format_rankings": {k.value: v for k, v in self.format_rankings.items()},
            "players": [p.to_dict() for p in self.players],
            "home_advantage": self.home_advantage
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Team':
        """Create Team from dictionary."""
        format_rankings = {MatchFormat(k): v for k, v in data.get("format_rankings", {}).items()}
        return cls(
            team_id=data["team_id"],
            name=data["name"],
            country=data["country"],
            format_rankings=format_rankings,
            players=[Player.from_dict(p) for p in data.get("players", [])],
            home_advantage=data.get("home_advantage", 0.0)
        )


@dataclass
class Match:
    """Represents a cricket match between two teams."""
    match_id: str
    team1: Team
    team2: Team
    format: MatchFormat
    venue: str = ""
    date: str = ""
    toss_winner: Optional[Team] = None
    toss_decision: str = ""  # "bat" or "field"
    winner: Optional[Team] = None
    result: str = ""  # e.g., "Team1 won by 5 wickets", "Match drawn"
    innings_scores: List[Dict] = field(default_factory=list)

    def simulate_toss(self) -> Team:
        """Simulate the coin toss and return the winner."""
        import random
        self.toss_winner = random.choice([self.team1, self.team2])
        # Toss winner decides to bat or field based on conditions
        self.toss_decision = random.choice(["bat", "field"])
        return self.toss_winner

    def to_dict(self) -> Dict:
        """Convert match to dictionary for serialization."""
        return {
            "match_id": self.match_id,
            "team1": self.team1.to_dict(),
            "team2": self.team2.to_dict(),
            "format": self.format.value,
            "venue": self.venue,
            "date": self.date,
            "toss_winner": self.toss_winner.to_dict() if self.toss_winner else None,
            "toss_decision": self.toss_decision,
            "winner": self.winner.to_dict() if self.winner else None,
            "result": self.result,
            "innings_scores": self.innings_scores
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Match':
        """Create Match from dictionary."""
        return cls(
            match_id=data["match_id"],
            team1=Team.from_dict(data["team1"]),
            team2=Team.from_dict(data["team2"]),
            format=MatchFormat(data["format"]),
            venue=data.get("venue", ""),
            date=data.get("date", ""),
            toss_winner=Team.from_dict(data["toss_winner"]) if data.get("toss_winner") else None,
            toss_decision=data.get("toss_decision", ""),
            winner=Team.from_dict(data["winner"]) if data.get("winner") else None,
            result=data.get("result", ""),
            innings_scores=data.get("innings_scores", [])
        )


def load_sample_data() -> Dict[str, Team]:
    """Load sample team and player data for testing."""
    # Sample data for demonstration - in reality this would come from APIs or databases
    teams_data = {
        "IND": {
            "team_id": "IND",
            "name": "India",
            "country": "India",
            "format_rankings": {
                "Test": 1,
                "ODI": 2,
                "T20": 1
            },
            "home_advantage": 0.1,
            "players": [
                {
                    "player_id": "vh Kohli",
                    "name": "Virat Kohli",
                    "team": "IND",
                    "role": "Batsman",
                    "batting_avg": 52.3,
                    "batting_sr": 93.2,
                    "bowling_avg": 99.0,
                    "bowling_sr": 0.0,
                    "economy": 5.0,
                    "recent_form": 0.8,
                    "experience": 250,
                    "is_captain": False
                },
                {
                    "player_id": "rb Sharma",
                    "name": "Rohit Sharma",
                    "team": "IND",
                    "role": "Batsman",
                    "batting_avg": 48.5,
                    "batting_sr": 89.1,
                    "bowling_avg": 99.0,
                    "bowling_sr": 0.0,
                    "economy": 5.0,
                    "recent_form": 0.7,
                    "experience": 220,
                    "is_captain": True
                },
                {
                    "player_id": "j bumrah",
                    "name": "Jasprit Bumrah",
                    "team": "IND",
                    "role": "Bowler",
                    "batting_avg": 10.0,
                    "batting_sr": 80.0,
                    "bowling_avg": 20.5,
                    "bowling_sr": 45.2,
                    "economy": 4.2,
                    "recent_form": 0.9,
                    "experience": 80,
                    "is_captain": False
                },
                {
                    "player_id": "r jadeja",
                    "name": "Ravindra Jadeja",
                    "team": "IND",
                    "role": "Allrounder",
                    "batting_avg": 36.8,
                    "batting_sr": 82.4,
                    "bowling_avg": 24.3,
                    "bowling_sr": 58.7,
                    "economy": 3.8,
                    "recent_form": 0.75,
                    "experience": 150,
                    "is_captain": False
                }
            ]
        },
        "AUS": {
            "team_id": "AUS",
            "name": "Australia",
            "country": "Australia",
            "format_rankings": {
                "Test": 2,
                "ODI": 3,
                "T20": 4
            },
            "home_advantage": 0.08,
            "players": [
                {
                    "player_id": "s smith",
                    "name": "Steve Smith",
                    "team": "AUS",
                    "role": "Batsman",
                    "batting_avg": 58.2,
                    "batting_sr": 58.9,
                    "bowling_avg": 99.0,
                    "bowling_sr": 0.0,
                    "economy": 5.0,
                    "recent_form": 0.85,
                    "experience": 180,
                    "is_captain": True
                },
                {
                    "player_id": "d warner",
                    "name": "David Warner",
                    "team": "AUS",
                    "role": "Batsman",
                    "batting_avg": 45.3,
                    "batting_sr": 92.7,
                    "bowling_avg": 99.0,
                    "bowling_sr": 0.0,
                    "economy": 5.0,
                    "recent_form": 0.7,
                    "experience": 160,
                    "is_captain": False
                },
                {
                    "player_id": "p cummins",
                    "name": "Pat Cummins",
                    "team": "AUS",
                    "role": "Bowler",
                    "batting_avg": 15.2,
                    "batting_sr": 75.3,
                    "bowling_avg": 21.8,
                    "bowling_sr": 42.1,
                    "economy": 4.1,
                    "recent_form": 0.8,
                    "experience": 100,
                    "is_captain": False
                },
                {
                    "player_id": "g maxwell",
                    "name": "Glenn Maxwell",
                    "team": "AUS",
                    "role": "Allrounder",
                    "batting_avg": 32.1,
                    "batting_sr": 125.6,
                    "bowling_avg": 30.5,
                    "bowling_sr": 35.2,
                    "economy": 5.2,
                    "recent_form": 0.6,
                    "experience": 120,
                    "is_captain": False
                }
            ]
        }
    }

    teams = {}
    for team_id, team_data in teams_data.items():
        teams[team_id] = Team.from_dict(team_data)

    return teams