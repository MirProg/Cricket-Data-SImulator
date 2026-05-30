"""
Tournament and season manager for cricket simulator.
Handles league formats, knockout tournaments, and points tables.
"""

from typing import List, Dict, Tuple, Optional
from enum import Enum
import itertools
from datetime import datetime, timedelta
import json
import os
from data.models import Team, Match, MatchFormat
from engine.simulator import CricketSimulator
import logging

logger = logging.getLogger(__name__)


class TournamentFormat(Enum):
    LEAGUE = "League"           # Round-robin league
    KNOCKOUT = "Knockout"       # Single elimination
    LEAGUE_KNOCKOUT = "LeagueKnockout"  # League stage followed by knockout
    DOUBLE_ROUND_ROBIN = "DoubleRoundRobin"  # Each team plays others twice


class Tournament:
    """Represents a cricket tournament or series."""

    def __init__(self, name: str, format: TournamentFormat,
                 match_format: MatchFormat, teams: List[Team]):
        self.name = name
        self.format = format
        self.match_format = match_format
        self.teams = teams
        self.matches: List[Match] = []
        self.points_table: Dict[str, Dict] = {}
        self.knockout_bracket: List[Dict] = []
        self.current_stage = "league"  # For hybrid formats
        self.created_at = datetime.now().isoformat()
        self.simulator = CricketSimulator()

        # Initialize points table
        self._initialize_points_table()

    def _initialize_points_table(self):
        """Initialize points table for all teams."""
        for team in self.teams:
            self.points_table[team.team_id] = {
                'team': team,
                'played': 0,
                'won': 0,
                'lost': 0,
                'tied': 0,
                'nr': 0,  # No result
                'points': 0,
                'net_run_rate': 0.0,
                'runs_for': 0,
                'runs_against': 0,
                'overs_for': 0,
                'overs_against': 0
            }

    def _update_points_table(self, match: Match):
        """Update points table based on match result."""
        # Extract teams and scores from match
        team1_id = match.team1.team_id
        team2_id = match.team2.team_id

        # Parse scores from innings
        # This is simplified - in reality we'd parse the actual scores
        if len(match.innings_scores) >= 2:
            # Simple assumption: first innings is team1, second is team2
            # This needs to be improved based on actual batting order
            team1_runs_wkts = match.innings_scores[0]['score'].split('/')
            team2_runs_wkts = match.innings_scores[1]['score'].split('/')

            try:
                team1_runs = int(team1_runs_wkts[0])
                team1_wickets = int(team1_runs_wkts[1]) if len(team1_runs_wkts) > 1 else 10
                team2_runs = int(team2_runs_wkts[0])
                team2_wickets = int(team2_runs_wkts[1]) if len(team2_runs_wkts) > 1 else 10
            except (ValueError, IndexError):
                # Fallback if parsing fails
                team1_runs, team1_wickets = 150, 5
                team2_runs, team2_wickets = 140, 5

            # Calculate overs (simplified)
            team1_overs = match.innings_scores[0].get('overs', 20)
            team2_overs = match.innings_scores[1].get('overs', 20)

            # Determine result
            if match.winner:
                if match.winner.team_id == team1_id:
                    # Team 1 won
                    self.points_table[team1_id]['won'] += 1
                    self.points_table[team2_id]['lost'] += 1
                    self.points_table[team1_id]['points'] += 2
                elif match.winner.team_id == team2_id:
                    # Team 2 won
                    self.points_table[team2_id]['won'] += 1
                    self.points_table[team1_id]['lost'] += 1
                    self.points_table[team2_id]['points'] += 2
            else:
                # Tie or no result
                self.points_table[team1_id]['tied'] += 1
                self.points_table[team2_id]['tied'] += 1
                self.points_table[team1_id]['points'] += 1
                self.points_table[team2_id]['points'] += 1

            # Update runs and overs for NRR calculation
            self.points_table[team1_id]['played'] += 1
            self.points_table[team2_id]['played'] += 1

            self.points_table[team1_id]['runs_for'] += team1_runs
            self.points_table[team1_id]['runs_against'] += team2_runs
            self.points_table[team2_id]['runs_for'] += team2_runs
            self.points_table[team2_id]['runs_against'] += team1_runs

            self.points_table[team1_id]['overs_for'] += team1_overs
            self.points_table[team1_id]['overs_against'] += team2_overs
            self.points_table[team2_id]['overs_for'] += team2_overs
            self.points_table[team2_id]['overs_against'] += team1_overs

        # Recalculate net run rates
        self._calculate_net_run_rates()

    def _calculate_net_run_rates(self):
        """Calculate net run rate for all teams."""
        for team_id, stats in self.points_table.items():
            if stats['overs_for'] > 0 and stats['overs_against'] > 0:
                runs_per_over_for = stats['runs_for'] / stats['overs_for']
                runs_per_over_against = stats['runs_against'] / stats['overs_against']
                stats['net_run_rate'] = runs_per_over_for - runs_per_over_against
            else:
                stats['net_run_rate'] = 0.0

    def generate_league_fixtures(self) -> List[Tuple[Team, Team]]:
        """
        Generate fixtures for league format.

        Returns:
            List of (home_team, away_team) tuples
        """
        fixtures = []

        if self.format == TournamentFormat.LEAGUE:
            # Single round-robin
            for i, team1 in enumerate(self.teams):
                for team2 in self.teams[i+1:]:
                    fixtures.append((team1, team2))

        elif self.format == TournamentFormat.DOUBLE_ROUND_ROBIN:
            # Double round-robin (home and away)
            for i, team1 in enumerate(self.teams):
                for team2 in self.teams[i+1:]:
                    fixtures.append((team1, team2))  # Team1 home
                    fixtures.append((team2, team1))  # Team2 home

        # For KNOCKOUT and LEAGUE_KNOCKOUT, fixtures are generated differently
        return fixtures

    def generate_knockout_bracket(self, teams: List[Team]) -> List[Dict]:
        """
        Generate knockout bracket for given teams.

        Args:
            teams: List of teams participating in knockout stage

        Returns:
            Bracket structure
        """
        # Simple implementation: seeding by points table position
        # In reality, this would use actual tournament seeding rules
        sorted_teams = sorted(teams, key=lambda t: (
            self.points_table[t.team_id]['points'],
            self.points_table[t.team_id]['net_run_rate']
        ), reverse=True)

        bracket = []
        num_teams = len(sorted_teams)

        # Handle byes if not power of 2
        # For simplicity, we'll just pair teams sequentially
        for i in range(0, num_teams, 2):
            if i + 1 < num_teams:
                bracket.append({
                    'match_number': len(bracket) + 1,
                    'team1': sorted_teams[i],
                    'team2': sorted_teams[i+1],
                    'winner': None
                })
            else:
                # Odd team gets a bye (advances automatically)
                bracket.append({
                    'match_number': len(bracket) + 1,
                    'team1': sorted_teams[i],
                    'team2': None,  # Bye
                    'winner': sorted_teams[i]
                })

        return bracket

    def simulate_league_stage(self):
        """Simulate all matches in the league stage."""
        logger.info(f"Simulating league stage for {self.name}")
        fixtures = self.generate_league_fixtures()

        for i, (team1, team2) in enumerate(fixtures):
            # Determine home advantage (simplified)
            venue = f"{team1.name} Home Ground" if i % 2 == 0 else f"{team2.name} Home Ground"

            logger.info(f"Simulating Match {i+1}: {team1.name} vs {team2.name} at {venue}")
            match = self.simulator.simulate_match(team1, team2, self.match_format, venue)
            self.matches.append(match)
            self._update_points_table(match)

            # Small delay to prevent flooding logs
            if (i + 1) % 5 == 0:
                logger.info(f"Completed {i+1} matches")

    def simulate_knockout_stage(self, teams: List[Team]) -> Team:
        """
        Simulate knockout stage and return the winner.

        Args:
            teams: List of teams entering knockout stage

        Returns:
            Winning team
        """
        logger.info(f"Simulating knockout stage with {len(teams)} teams")
        current_teams = teams[:]
        round_number = 1

        while len(current_teams) > 1:
            logger.info(f"Knockout Round {round_number}: {len(current_teams)} teams")
            bracket = self.generate_knockout_bracket(current_teams)
            winners = []

            for match_info in bracket:
                team1 = match_info['team1']
                team2 = match_info['team2']

                if team2 is None:  # Bye
                    winners.append(team1)
                    logger.info(f"{team1.name} advances byes")
                    continue

                # Determine venue (neutral for knockout)
                venue = f"Neutral Venue - QF{round_number}" if round_number <= 2 else f"Neutral Venue - SF{round_number-2}"

                logger.info(f"Simulating: {team1.name} vs {team2.name} at {venue}")
                match = self.simulator.simulate_match(team1, team2, self.match_format, venue)
                self.matches.append(match)
                self._update_points_table(match)

                if match.winner:
                    winners.append(match.winner)
                    logger.info(f"{match.winner.name} wins")
                else:
                    # Fallback if no winner determined
                    winners.append(team1)
                    logger.info(f"{team1.name} wins by default")

            current_teams = winners
            round_number += 1

        return current_teams[0] if current_teams else None

    def simulate_tournament(self) -> Dict:
        """
        Simulate the entire tournament based on its format.

        Returns:
            Dictionary with tournament results
        """
        logger.info(f"Starting tournament simulation: {self.name}")
        logger.info(f"Format: {self.format.value}, Match Format: {self.match_format.value}")
        logger.info(f"Participating teams: {[t.name for t in self.teams]}")

        if self.format == TournamentFormat.LEAGUE or self.format == TournamentFormat.DOUBLE_ROUND_ROBIN:
            # Pure league format
            self.simulate_league_stage()
            winner = self._get_league_winner()

        elif self.format == TournamentFormat.KNOCKOUT:
            # Pure knockout
            winner = self.simulate_knockout_stage(self.teams)

        elif self.format == TournamentFormat.LEAGUE_KNOCKOUT:
            # League stage followed by knockout
            self.simulate_league_stage()

            # Top 4 teams advance to knockout (standard format)
            qualified_teams = self._get_qualified_teams(4)
            logger.info(f"Qualified teams for knockout: {[t.name for t in qualified_teams]}")

            winner = self.simulate_knockout_stage(qualified_teams)

        # Generate final standings
        standings = self._generate_standings()

        results = {
            'tournament_name': self.name,
            'format': self.format.value,
            'match_format': self.match_format.value,
            'teams': [t.name for t in self.teams],
            'total_matches_simulated': len(self.matches),
            'winner': winner.name if winner else None,
            'points_table': {tid: {k: v for k, v in stats.items() if k != 'team'}
                           for tid, stats in self.points_table.items()},
            'standings': standings,
            'matches': [
                {
                    'match_id': m.match_id,
                    'team1': m.team1.name,
                    'team2': m.team2.name,
                    'winner': m.winner.name if m.winner else None,
                    'result': m.result,
                    'venue': m.venue,
                    'date': m.date
                }
                for m in self.matches
            ]
        }

        logger.info(f"Tournament completed! Winner: {winner.name if winner else 'TBD'}")
        return results

    def _get_league_winner(self) -> Optional[Team]:
        """Get the winner based on points table."""
        if not self.points_table:
            return None

        sorted_teams = sorted(
            self.points_table.items(),
            key=lambda x: (x[1]['points'], x[1]['net_run_rate']),
            reverse=True
        )

        return sorted_teams[0][1]['team'] if sorted_teams else None

    def _get_qualified_teams(self, num_teams: int) -> List[Team]:
        """Get top teams from points table for knockout qualification."""
        sorted_teams = sorted(
            self.points_table.items(),
            key=lambda x: (x[1]['points'], x[1]['net_run_rate']),
            reverse=True
        )

        return [item[1]['team'] for item in sorted_teams[:num_teams]]

    def _generate_standings(self) -> List[Dict]:
        """Generate final standings for the tournament."""
        standings = []
        for team_id, stats in self.points_table.items():
            team_obj = stats['team']
            standings.append({
                'position': 0,  # Will be set after sorting
                'team_id': team_id,
                'team_name': team_obj.name,
                'played': stats['played'],
                'won': stats['won'],
                'lost': stats['lost'],
                'tied': stats['tied'],
                'nr': stats['nr'],
                'points': stats['points'],
                'net_run_rate': round(stats['net_run_rate'], 3),
                'for': stats['runs_for'],
                'against': stats['runs_against']
            })

        # Sort by points, then net run rate
        standings.sort(key=lambda x: (x['points'], x['net_run_rate']), reverse=True)

        # Assign positions
        for i, standing in enumerate(standings):
            standing['position'] = i + 1

        return standings

    def save_tournament(self, filepath: str):
        """Save tournament results to file."""
        results = self.simulate_tournament()
        try:
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"Tournament results saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving tournament: {e}")

    def load_tournament(self, filepath: str):
        """Load tournament results from file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            logger.info(f"Tournament results loaded from {filepath}")
            return data
        except Exception as e:
            logger.error(f"Error loading tournament: {e}")
            return None


def main():
    """Test the tournament manager."""
    # Create sample teams
    from ..data.models import load_sample_data
    teams_dict = load_sample_data()
    teams = list(teams_dict.values())

    # Create a test tournament
    tournament = Tournament(
        name="Test Cricket Series",
        format=TournamentFormat.LEAGUE_KNOCKOUT,
        match_format=MatchFormat.T20,
        teams=teams
    )

    # Simulate tournament
    results = tournament.simulate_tournament()

    print("\n=== TOURNAMENT RESULTS ===")
    print(f"Tournament: {results['tournament_name']}")
    print(f"Winner: {results['winner']}")
    print(f"Total Matches: {results['total_matches_simulated']}")

    print("\n=== FINAL STANDINGS ===")
    for standing in results['standings']:
        print(f"{standing['position']}. {standing['team_name']} - {standing['points']} pts "
              f"(NRR: {standing['net_run_rate']})")

    print("\n=== POINTS TABLE ===")
    for team_id, stats in results['points_table'].items():
        print(f"{stats['team_name']}: P{stats['played']} W{stats['won']} L{stats['lost']} "
              f"T{stats['tied']} Pts{stats['points']} NRR{stats['net_run_rate']:.3f}")


if __name__ == "__main__":
    main()