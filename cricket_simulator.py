#!/usr/bin/env python3
"""
Cricket Simulator - Main Entry Point
A full-featured cricket simulator that works with numbers only.
"""

import argparse
import sys
import os
import json
from typing import List, Dict

# Add the project root to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Ensure stdout can handle emojis on Windows
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from data.collector import CricketDataCollector
from data.models import Team, MatchFormat, PlayerRole
from data.live import LiveTracker, display_live_matches, display_commentary
from engine.simulator import CricketSimulator
from ai.predictor import AIPredictor
from ai.train import train_advanced_model
from tournament.manager import Tournament, TournamentFormat
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cricket_simulator.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class CricketSimulatorCLI:
    """Command-line interface for the cricket simulator."""

    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), "data")
        self.collector = CricketDataCollector(self.data_dir)
        self.simulator = CricketSimulator()
        self.predictor = None # Initialized on demand
        self.live_tracker = LiveTracker()
        self.teams: Dict[str, Team] = {}

    def load_teams(self):
        """Load team data from storage or fetch fresh data."""
        logger.info("Loading team data...")
        self.teams = self.collector.collect_all_data()
        logger.info(f"Loaded {len(self.teams)} teams")

    def list_teams(self):
        """Display available teams."""
        if not self.teams:
            self.load_teams()

        print("\n=== AVAILABLE TEAMS ===")
        for team_id, team in sorted(self.teams.items(), key=lambda x: x[1].name):
            print(f"{team_id}: {team.name} ({team.country})")
            print(f"  Players: {len(team.players)}")
            if team.format_rankings:
                rankings = ", ".join([f"{fmt.value}: {rank}" for fmt, rank in team.format_rankings.items()])
                print(f"  Rankings: {rankings}")
            print()

    def simulate_match(self, team1_id: str, team2_id: str, format_str: str,
                      venue: str = "", use_ai: bool = False):
        """
        Simulate a match between two teams.

        Args:
            team1_id: ID of first team
            team2_id: ID of second team
            format_str: Match format (Test, ODI, T20)
            venue: Match venue
            use_ai: Whether to use AI enhancement
        """
        if not self.teams:
            self.load_teams()

        if team1_id not in self.teams:
            print(f"Error: Team '{team1_id}' not found")
            return

        if team2_id not in self.teams:
            print(f"Error: Team '{team2_id}' not found")
            return

        team1 = self.teams[team1_id]
        team2 = self.teams[team2_id]

        try:
            match_format = MatchFormat(format_str.upper())
        except ValueError:
            print(f"Error: Invalid format '{format_str}'. Use Test, ODI, or T20")
            return

        logger.info(f"Simulating match: {team1.name} vs {team2.name} ({match_format.value})")

        # Optional AI prediction
        if use_ai:
            print("\n=== INITIALIZING AI MATCH SIMULATOR ===")
            if not self.predictor:
                self.predictor = AIPredictor()
            if self.predictor.is_loaded:
                print("PyTorch model loaded successfully. Balls will be simulated using AI.")
            else:
                print("Warning: PyTorch model not found or failed to load. Run 'ai-train' first. Falling back to heuristics.")
            print()

        # Simulate the match
        match = self.simulator.simulate_match(team1, team2, match_format, venue, ai_predictor=self.predictor if use_ai else None)

        # Display results
        self._display_match_result(match)

    def _display_match_result(self, match):
        """Display the result of a simulated match."""
        print("\n=== MATCH RESULT ===")
        print(f"Match: {match.team1.name} vs {match.team2.name}")
        print(f"Format: {match.format.value}")
        print(f"Venue: {match.venue}")
        print(f"Date: {match.date}")
        print(f"Toss: {match.toss_winner.name} chose to {match.toss_decision}")
        print()

        print("Innings Scores:")
        for innings in match.innings_scores:
            print(f"  Inning {innings['innings']}: {innings['team']} {innings['score']} ({innings['overs']} overs)")

        print()
        if match.winner:
            print(f"RESULT: {match.result}")
        else:
            print(f"RESULT: {match.result}")

        # Show brief scorecard
        print("\n=== BRIEF SCORECARD ===")
        if len(match.innings_scores) >= 2:
            # First innings
            team1_name = match.innings_scores[0]['team']
            team1_score = match.innings_scores[0]['score']
            team1_overs = match.innings_scores[0]['overs']

            # Second innings
            team2_name = match.innings_scores[1]['team']
            team2_score = match.innings_scores[1]['score']
            team2_overs = match.innings_scores[1]['overs']

            print(f"{team1_name}: {team1_score} ({team1_overs} overs)")
            print(f"{team2_name}: {team2_score} ({team2_overs} overs)")

    def simulate_tournament(self, name: str, format_str: str, match_format_str: str,
                           team_ids: List[str] = None):
        """
        Simulate a tournament.

        Args:
            name: Tournament name
            format_str: Tournament format (League, Knockout, LeagueKnockout, DoubleRoundRobin)
            match_format_str: Match format (Test, ODI, T20)
            team_ids: List of team IDs to include (None for all teams)
        """
        if not self.teams:
            self.load_teams()

        # Select teams
        if team_ids:
            teams = [self.teams[tid] for tid in team_ids if tid in self.teams]
            if not teams:
                print("Error: No valid teams selected")
                return
        else:
            teams = list(self.teams.values())

        if len(teams) < 2:
            print("Error: Need at least 2 teams for a tournament")
            return

        try:
            # Try to match tournament format case-insensitively
            tournament_format = None
            for fmt in TournamentFormat:
                if fmt.value.lower() == format_str.lower():
                    tournament_format = fmt
                    break
            if tournament_format is None:
                raise ValueError(f"Invalid tournament format: {format_str}")

            # Match format is already uppercase in enum values
            match_format = MatchFormat(match_format_str.upper())
        except ValueError as e:
            print(f"Error: {e}")
            return

        logger.info(f"Starting tournament: {name}")
        print(f"\n=== SIMULATING TOURNAMENT: {name} ===")
        print(f"Format: {tournament_format.value}")
        print(f"Match Format: {match_format.value}")
        print(f"Teams: {len(teams)}")
        print(f"Team List: {', '.join([t.name for t in teams])}")
        print()

        # Create and simulate tournament
        tournament = Tournament(
            name=name,
            format=tournament_format,
            match_format=match_format,
            teams=teams
        )

        results = tournament.simulate_tournament()

        # Display results
        self._display_tournament_results(results)

    def _display_tournament_results(self, results):
        """Display tournament results."""
        print("=== TOURNAMENT RESULTS ===")
        print(f"Tournament: {results['tournament_name']}")
        print(f"Format: {results['format']}")
        print(f"Match Format: {results['match_format']}")
        print(f"Winner: {results['winner']}")
        print(f"Total Matches: {results['total_matches_simulated']}")
        print()

        print("=== FINAL STANDINGS ===")
        print(f"{'Pos':<4} {'Team':<20} {'P':<3} {'W':<3} {'L':<3} {'T':<3} {'Pts':<4} {'NRR':<6}")
        print("-" * 50)
        for standing in results['standings']:
            print(f"{standing['position']:<4} {standing['team_name']:<20} "
                  f"{standing['played']:<3} {standing['won']:<3} {standing['lost']:<3} "
                  f"{standing['tied']:<3} {standing['points']:<4} {standing['net_run_rate']:<6.3f}")
        print()

        print("=== POINTS TABLE DETAILS ===")
        # Get team names from the teams list in results
        team_names = {team['team_id']: team['team_name'] for team in results['standings']}
        for team_id, stats in results['points_table'].items():
            team_name = team_names.get(team_id, f"Team {team_id}")
            print(f"{team_name}:")
            print(f"  Played: {stats['played']}, Won: {stats['won']}, Lost: {stats['lost']}, Tied: {stats['tied']}")
            print(f"  Points: {stats['points']}, Net Run Rate: {stats['net_run_rate']:.3f}")
            print(f"  Runs For: {stats['runs_for']}, Runs Against: {stats['runs_against']}")
            print()

    def update_data(self):
        """Update live data from sources."""
        print("Updating live cricket data...")
        self.collector.update_live_data()
        # Reload teams with fresh data
        self.teams = self.collector.collect_all_data()
        print(f"Data updated. Loaded {len(self.teams)} teams.")

    def fetch_data(self):
        """Force a fresh scrape of all data from ESPN Cricinfo Statsguru."""
        print("Clearing cache and fetching ALL data from ESPN Cricinfo Statsguru...")
        print("This will scrape every team and every player in cricket history.")
        print("Estimated time: 10-25 minutes depending on connection.\n")
        self.collector.update_live_data()  # Clears cache
        self.teams = self.collector.collect_all_data()  # Re-scrapes
        print(f"\nFetch complete. Loaded {len(self.teams)} teams.")

    def show_live_matches(self):
        """Display currently live cricket matches."""
        print("\nFetching live cricket matches...")
        matches = self.live_tracker.get_live_matches()
        display_live_matches(matches)

    def show_commentary(self, match_id: str, innings: int = 1):
        """Display ball-by-ball commentary for a match."""
        print(f"\nFetching commentary for match {match_id}...")
        commentary = self.live_tracker.get_commentary(match_id, innings)
        display_commentary(commentary, match_id)

    def start_live_feed(self, match_id: str, interval: int = 30):
        """Start live commentary feed for a match."""
        self.live_tracker.start_live_feed(match_id, interval)

    def show_player_stats(self, player_name: str):
        """Search and display stats for a specific player."""
        if not self.teams:
            self.load_teams()

        found = []
        search = player_name.lower()
        for team_id, team in self.teams.items():
            for player in team.players:
                if search in player.name.lower():
                    found.append((team, player))

        if not found:
            print(f"No players found matching '{player_name}'")
            return

        print(f"\n=== PLAYER SEARCH: '{player_name}' ({len(found)} results) ===")
        for team, player in found[:20]:
            print(f"\n  {player.name} ({team.name})")
            print(f"    Role: {player.role.value}")
            print(f"    Batting Avg: {player.batting_avg:.2f}  |  SR: {player.batting_sr:.2f}")
            if player.role in (PlayerRole.BOWLER, PlayerRole.ALLROUNDER) or player.bowling_avg < 90:
                print(f"    Bowling Avg: {player.bowling_avg:.2f}  |  Econ: {player.economy:.2f}  |  SR: {player.bowling_sr:.2f}")
            print(f"    Experience: {player.experience} matches  |  Form: {player.recent_form:.2f}")
            flags = []
            if player.is_captain:
                flags.append("Captain")
            if player.is_wicketkeeper:
                flags.append("Wicketkeeper")
            if flags:
                print(f"    Flags: {', '.join(flags)}")
        if len(found) > 20:
            print(f"\n  ... and {len(found) - 20} more")


def main():
    """Main entry point for the cricket simulator CLI."""
    parser = argparse.ArgumentParser(
        description="Cricket Simulator - Full-featured cricket simulator with ESPN Cricinfo data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s fetch                                        # Scrape ALL data from ESPN Cricinfo
  %(prog)s teams                                        # List all teams
  %(prog)s player "Virat Kohli"                         # Search player stats
  %(prog)s match IND AUS T20 --venue "Mumbai"           # Simulate a match
  %(prog)s match ENG NZ ODI --use-ai                    # Match with AI prediction
  %(prog)s tournament "World Cup" LeagueKnockout T20    # Simulate tournament
  %(prog)s live                                         # Show live matches
  %(prog)s commentary 12345                             # Ball-by-ball commentary
  %(prog)s livefeed 12345                               # Real-time commentary feed
  %(prog)s update                                       # Refresh cached data
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Fetch command — scrape all data from ESPN Cricinfo
    subparsers.add_parser('fetch', help='Scrape ALL historical data from ESPN Cricinfo Statsguru')

    # AI Train command
    subparsers.add_parser('ai-train', help='Train the PyTorch Ball-by-ball neural network')

    # Teams command
    subparsers.add_parser('teams', help='List available teams')

    # Player search command
    player_parser = subparsers.add_parser('player', help='Search player stats')
    player_parser.add_argument('name', help='Player name to search for')

    # Match command
    match_parser = subparsers.add_parser('match', help='Simulate a match between two teams')
    match_parser.add_argument('team1', help='First team ID')
    match_parser.add_argument('team2', help='Second team ID')
    match_parser.add_argument('format', choices=['Test', 'ODI', 'T20'], help='Match format')
    match_parser.add_argument('--venue', default='Neutral Venue', help='Match venue')
    match_parser.add_argument('--use-ai', action='store_true', help='Use AI enhancement for prediction')

    # Tournament command
    tournament_parser = subparsers.add_parser('tournament', help='Simulate a tournament')
    tournament_parser.add_argument('name', help='Tournament name')
    tournament_parser.add_argument('format', choices=['League', 'Knockout', 'LeagueKnockout', 'DoubleRoundRobin'],
                                 help='Tournament format')
    tournament_parser.add_argument('match_format', choices=['Test', 'ODI', 'T20'], help='Match format')
    tournament_parser.add_argument('teams', nargs='*', help='Team IDs to include (optional, defaults to all)')

    # Live matches command
    subparsers.add_parser('live', help='Show currently live cricket matches')

    # Commentary command
    comm_parser = subparsers.add_parser('commentary', help='Show ball-by-ball commentary for a match')
    comm_parser.add_argument('match_id', help='ESPN match ID')
    comm_parser.add_argument('--innings', type=int, default=1, help='Innings number (default: 1)')

    # Live feed command
    feed_parser = subparsers.add_parser('livefeed', help='Start real-time commentary feed for a match')
    feed_parser.add_argument('match_id', help='ESPN match ID')
    feed_parser.add_argument('--interval', type=int, default=30, help='Polling interval in seconds (default: 30)')

    # Update command
    subparsers.add_parser('update', help='Clear cache and refresh data')

    args = parser.parse_args()

    # Initialize CLI
    cli = CricketSimulatorCLI()

    if args.command == 'fetch':
        cli.fetch_data()
    elif args.command == 'teams':
        cli.list_teams()
    elif args.command == 'player':
        cli.show_player_stats(args.name)
    elif args.command == 'match':
        cli.simulate_match(args.team1, args.team2, args.format, args.venue, args.use_ai)
    elif args.command == 'tournament':
        cli.simulate_tournament(args.name, args.format, args.match_format, args.teams)
    elif args.command == 'live':
        cli.show_live_matches()
    elif args.command == 'commentary':
        cli.show_commentary(args.match_id, args.innings)
    elif args.command == 'livefeed':
        cli.start_live_feed(args.match_id, args.interval)
    elif args.command == 'update':
        cli.update_data()
    elif args.command == 'ai-train':
        train_advanced_model()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()