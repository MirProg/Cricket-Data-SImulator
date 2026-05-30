"""
Ball-by-ball cricket match simulator.
Simulates cricket matches based on player statistics and match conditions.
"""

import random
import math
import numpy as np
from typing import Dict, List, Tuple, Optional
from enum import Enum
from data.models import Team, Player, Match, MatchFormat, PlayerRole


class ShotType(Enum):
    """Types of shots a batsman can play."""
    DEFENSIVE = "defensive"
    DRIVE = "drive"
    PULL = "pull"
    HOOK = "hook"
    CUT = "cut"
    SWEEP = "sweep"
    LOFTED = "lofted"
    GLANCE = "glance"


class BowlingType(Enum):
    """Types of bowling deliveries."""
    FAST = "fast"
    MEDIUM = "medium"
    SPIN = "spin"
    SWING = "swing"


class MatchEvent(Enum):
    """Possible events in a cricket ball."""
    DOT_BALL = "dot"
    RUN_1 = "1"
    RUN_2 = "2"
    RUN_3 = "3"
    RUN_4 = "4"
    RUN_5 = "5"
    SIX = "6"
    WICKET = "wicket"
    WIDE = "wide"
    NO_BALL = "no ball"
    BYE = "bye"
    LEG_BYE = "leg bye"


class CricketSimulator:
    """Simulates cricket matches ball by ball."""

    def __init__(self):
        # Base probabilities for different events (can be adjusted based on conditions)
        self.base_probabilities = {
            MatchEvent.DOT_BALL: 0.45,
            MatchEvent.RUN_1: 0.25,
            MatchEvent.RUN_2: 0.08,
            MatchEvent.RUN_3: 0.01,
            MatchEvent.RUN_4: 0.08,
            MatchEvent.SIX: 0.03,
            MatchEvent.WICKET: 0.08,
            MatchEvent.WIDE: 0.02,
            MatchEvent.NO_BALL: 0.01,
            MatchEvent.BYE: 0.02,
            MatchEvent.LEG_BYE: 0.01
        }

    def calculate_batting_score(self, batsman: Player, bowler: Player,
                              match_format: MatchFormat, pitch_factor: float = 1.0,
                              weather_factor: float = 1.0) -> float:
        """
        Calculate batsman's scoring potential against a specific bowler.

        Returns a score representing the batsman's ability to score runs.
        """
        # Base scoring ability from batting average and strike rate
        batting_skill = (batsman.batting_avg / 50.0) * 0.4 + (batsman.batting_sr / 100.0) * 0.6

        # Adjust for bowler quality (lower bowling avg = better bowler)
        if bowler.bowling_avg < 50:
            bowling_difficulty = (30.0 / bowler.bowling_avg)  # Better bowlers have lower averages
        else:
            bowling_difficulty = 0.8  # For part-time bowlers

        # Form factor
        form_factor = 0.5 + batsman.recent_form  # Ranges from 0.5 to 1.5

        # Match format factors (T20 favors aggressive batting)
        format_factors = {
            MatchFormat.TEST: 0.8,
            MatchFormat.ODI: 1.0,
            MatchFormat.T20: 1.3
        }
        format_factor = format_factors[match_format]

        # Combined score
        score = batting_skill * (1.0 / max(bowling_difficulty, 0.5)) * form_factor * format_factor
        score *= pitch_factor * weather_factor

        return max(0.1, min(3.0, score))  # Keep within reasonable bounds

    def calculate_wicket_probability(self, batsman: Player, bowler: Player,
                                   match_format: MatchFormat) -> float:
        """
        Calculate probability of wicket on a given ball.
        """
        # Base wicket probability
        base_wicket_prob = 0.08

        # Bowler skill factor (lower avg = better bowler = higher wicket chance)
        if bowler.bowling_avg > 0:
            bowling_skill = max(0.5, min(2.0, 30.0 / bowler.bowling_avg))
        else:
            bowling_skill = 0.5  # For very poor bowlers

        # Batsman vulnerability (higher avg = less likely to get out)
        if batsman.batting_avg > 0:
            batsman_vulnerability = max(0.5, min(2.0, 50.0 / batsman.batting_avg))
        else:
            batsman_vulnerability = 2.0  # For very poor batsmen

        # Form factor
        batsman_form_factor = 1.5 - batsman.recent_form  # Poor form = higher wicket chance
        bowler_form_factor = 0.5 + bowler.recent_form    # Good form = higher wicket chance

        # Match format (more wickets in T20 due to aggressive play)
        format_factors = {
            MatchFormat.TEST: 0.9,
            MatchFormat.ODI: 1.0,
            MatchFormat.T20: 1.2
        }
        format_factor = format_factors[match_format]

        probability = base_wicket_prob * bowling_skill * batsman_vulnerability * \
                     batsman_form_factor * bowler_form_factor * format_factor

        return max(0.01, min(0.25, probability))  # Keep within reasonable bounds

    def simulate_ball(self, batsman: Player, bowler: Player,
                     match: Match, over_number: int, ball_number: int,
                     ai_predictor=None) -> Tuple[MatchEvent, int]:
        """
        Simulate a single ball and return the event and runs scored.

        Returns:
            Tuple of (MatchEvent, runs_scored)
        """
        # Match conditions factors
        pitch_factor = random.uniform(0.8, 1.2)  # Pitch can help batsmen or bowlers
        weather_factor = random.uniform(0.9, 1.1)  # Weather effects

        if ai_predictor and ai_predictor.is_loaded:
            # Format encoding
            if match.format == MatchFormat.TEST:
                fmt_enc = 0.0
            elif match.format == MatchFormat.ODI:
                fmt_enc = 0.5
            else:
                fmt_enc = 1.0
                
            # Query PyTorch Neural Network for exact outcome probabilities
            probs = ai_predictor.predict_ball(
                bat_avg=batsman.batting_avg,
                bat_sr=batsman.batting_sr,
                bat_form=batsman.recent_form,
                bowl_avg=bowler.bowling_avg,
                bowl_econ=bowler.economy,
                bowl_form=bowler.recent_form,
                match_format=fmt_enc,
                pitch_factor=pitch_factor * weather_factor
            )
            
            # Map probabilities to events
            events = [
                MatchEvent.WICKET,
                MatchEvent.DOT_BALL,
                MatchEvent.RUN_1,
                MatchEvent.RUN_2,
                MatchEvent.RUN_3,
                MatchEvent.RUN_4,
                MatchEvent.SIX
            ]
            event = np.random.choice(events, p=probs)
        else:
            # Fallback to simple mathematical heuristics
            batting_score = self.calculate_batting_score(batsman, bowler, match.format,
                                                       pitch_factor, weather_factor)
            wicket_prob = self.calculate_wicket_probability(batsman, bowler, match.format)
    
            # Adjust base probabilities
            adjusted_probs = self.base_probabilities.copy()
    
            # Scale run probabilities based on batting score
            run_factor = 0.5 + batting_score  # Makes scores range from 0.5 to 1.5
            adjusted_probs[MatchEvent.RUN_1] *= run_factor
            adjusted_probs[MatchEvent.RUN_2] *= run_factor
            adjusted_probs[MatchEvent.RUN_3] *= run_factor
            adjusted_probs[MatchEvent.RUN_4] *= run_factor
            adjusted_probs[MatchEvent.SIX] *= run_factor
    
            # Adjust wicket probability
            adjusted_probs[MatchEvent.WICKET] = wicket_prob
    
            # Ensure probabilities sum to 1.0
            total_prob = sum(adjusted_probs.values())
            if total_prob != 1.0:
                # Normalize probabilities
                for ev in adjusted_probs:
                    adjusted_probs[ev] /= total_prob
    
            # Select event based on probabilities
            evs = list(adjusted_probs.keys())
            probabilities = list(adjusted_probs.values())
            event = random.choices(evs, weights=probabilities)[0]

        # Calculate runs scored based on event
        runs_mapping = {
            MatchEvent.DOT_BALL: 0,
            MatchEvent.RUN_1: 1,
            MatchEvent.RUN_2: 2,
            MatchEvent.RUN_3: 3,
            MatchEvent.RUN_4: 4,
            MatchEvent.SIX: 6,
            MatchEvent.WICKET: 0,
            MatchEvent.WIDE: 1,  # Wides count as extras
            MatchEvent.NO_BALL: 1,  # No balls count as extras
            MatchEvent.BYE: 1,
            MatchEvent.LEG_BYE: 1
        }

        runs = runs_mapping[event]
        return event, runs

    def generate_commentary(self, bowler: Player, batsman: Player, event: MatchEvent, runs: int) -> str:
        """Generate natural language AI commentary for a ball."""
        bname = bowler.name.split()[-1]
        fname = batsman.name.split()[-1]
        
        if event == MatchEvent.WICKET:
            return random.choice([
                f"BOWLED HIM! {bname} completely dismantles the stumps! {fname} has to walk back.",
                f"EDGED AND TAKEN! Brilliant bowling from {bname}, {fname} departs.",
                f"Given lbw! {bname} traps {fname} right in front. Dead plumb."
            ])
        elif event == MatchEvent.SIX:
            return random.choice([
                f"MASSIVE! {fname} reads it early and sends {bname} miles back into the stands for SIX!",
                f"Oh what a shot. Stand and deliver from {fname}, cleared the rope easily.",
                f"SMACKED! {fname} absolutely deposits {bname} over deep mid-wicket for a maximum!"
            ])
        elif event == MatchEvent.RUN_4:
            return random.choice([
                f"Beautiful shot! {fname} drives {bname} through the covers for a boundary.",
                f"Pierced the gap to perfection! Four runs to {fname}.",
                f"Short from {bname}, and {fname} pulls it away violently to the square leg boundary."
            ])
        elif event == MatchEvent.DOT_BALL:
            return random.choice([
                f"Solid defense by {fname} to a good length delivery from {bname}.",
                f"{bname} beats the edge! Lovely movement off the pitch.",
                f"Played straight to the fielder. No run."
            ])
        else:
            return f"Driven away by {fname} for {runs} run{'s' if runs > 1 else ''} off {bname}."

    def simulate_over(self, batting_team: Team, bowling_team: Team,
                     match: Match, over_number: int, striker: Player,
                     non_striker: Player, bowler: Player, ai_predictor=None, on_ball=None) -> Tuple[List[Tuple[MatchEvent, int]], Player, Player]:
        """
        Simulate a single over (6 balls).

        Returns:
            Tuple of (list of (event, runs) for each ball, updated striker, updated non_striker)
        """
        over_events = []
        current_striker = striker
        current_non_striker = non_striker

        for ball in range(1, 7):
            event, runs = self.simulate_ball(current_striker, bowler, match,
                                           over_number, ball, ai_predictor)
            
            comm = self.generate_commentary(bowler, current_striker, event, runs)
            if on_ball:
                on_ball(event, runs, comm, over_number, ball)
                
            over_events.append((event, runs))

            # Update scores and handle events
            if event == MatchEvent.WICKET:
                # Striker is out, need new batsman
                # For simplicity, we'll just rotate to next available batsman
                # In reality, this would depend on batting order
                pass
            elif event in [MatchEvent.RUN_1, MatchEvent.RUN_3]:
                # Odd runs cause striker and non-striker to switch ends
                current_striker, current_non_striker = current_non_striker, current_striker
            elif event in [MatchEvent.WIDE, MatchEvent.NO_BALL]:
                # Wide or no ball: batsman faces another ball (don't increment ball count)
                # For simplicity, we'll still count it but note it's an extra ball
                pass

        return over_events, current_striker, current_non_striker

    def simulate_innings(self, batting_team: Team, bowling_team: Team, match: Match,
                        target: int = None, ai_predictor=None, on_ball=None) -> Dict:
        """
        Simulate a complete innings.

        Args:
            batting_team: Team batting
            bowling_team: Team bowling
            match: Match object
            target: Target score to chase (None if setting target)
            ai_predictor: PyTorch neural net for prediction (optional)

        Returns:
            Dictionary with innings results
        """
        # Select opening batsmen and bowler
        xi = batting_team.get_playing_xi()
        bowlers = bowling_team.get_bowlers()

        if len(xi) < 2:
            # Not enough batsmen, pad with sample data
            xi = xi[:2] if len(xi) >= 2 else xi + [
                Player("dummy1", "Dummy Batter", batting_team.name, PlayerRole.BATSMAN, 10.0, 80.0, 99.0, 0.0, 5.0, 0.1, 0),
                Player("dummy2", "Dummy Batter", batting_team.name, PlayerRole.BATSMAN, 10.0, 80.0, 99.0, 0.0, 5.0, 0.1, 0)
            ][:2-len(xi)]

        striker = xi[0]
        non_striker = xi[1] if len(xi) > 1 else striker
        bowler = bowlers[0] if bowlers else Player("dummy_bowler", "Dummy Bowler", bowling_team.name, PlayerRole.BOWLER, 10.0, 80.0, 30.0, 40.0, 4.5, 0.5, 0)

        # Initialize innings tracking
        total_runs = 0
        wickets = 0
        overs_bowled = 0
        balls_bowled = 0
        over_scores = []
        batsman_scores = {p.player_id: {"runs": 0, "balls": 0, "4s": 0, "6s": 0, "out": False} for p in xi}
        bowler_stats = {p.player_id: {"overs": 0, "runs": 0, "wickets": 0, "economy": 0.0} for p in bowlers}

        # Track batting order index
        batting_index = 2  # Next batsman to come in

        # Simulate overs
        max_overs = 20 if match.format == MatchFormat.T20 else (50 if match.format == MatchFormat.ODI else 400)  # Simplified

        while overs_bowled < max_overs and wickets < 10:
            # Check if target is reached (for second innings)
            if target and total_runs >= target:
                break

            # Simulate one over
            over_events, striker, non_striker = self.simulate_over(
                batting_team, bowling_team, match, overs_bowled + 1, striker, non_striker, bowler, ai_predictor, on_ball
            )

            over_runs = sum(runs for _, runs in over_events)
            over_wickets = sum(1 for event, _ in over_events if event == MatchEvent.WICKET)

            total_runs += over_runs
            wickets += over_wickets
            overs_bowled += 1
            balls_bowled += 6  # Simplified - doesn't account for wides/no balls properly

            over_scores.append({
                "over": overs_bowled,
                "runs": over_runs,
                "wickets": over_wickets,
                "total": total_runs,
                "events": [(event.value, runs) for event, runs in over_events]
            })

            # Change bowler after every over (simplified)
            if overs_bowled % 2 == 0 and len(bowlers) > 1:  # Change bowler every 2 overs
                bowler_idx = (overs_bowled // 2) % len(bowlers)
                bowler = bowlers[bowler_idx]

            # Handle wickets - bring in new batsman
            if over_wickets > 0 and batting_index < len(xi):
                # Simplified: replace striker if he's out, otherwise non-striker
                # In reality, we'd need to track who got out
                if random.choice([True, False]):  # 50% chance striker got out
                    striker = xi[batting_index]
                else:
                    non_striker = xi[batting_index]
                batting_index += 1

        # Calculate batting statistics (simplified)
        for event, runs in [(event, runs) for over in over_scores for event, runs in over["events"]]:
            if event in ['1', '2', '3']:
                # For simplicity, assign runs to striker (not accurate but functional)
                striker_id = striker.player_id
                if striker_id in batsman_scores:
                    batsman_scores[striker_id]["runs"] += int(event)
                    batsman_scores[striker_id]["balls"] += 1
                    if event == '4':
                        batsman_scores[striker_id]["4s"] += 1
                    elif event == '6':
                        batsman_scores[striker_id]["6s"] += 1
            elif event == 'WICKET':
                # Mark striker as out (simplified)
                batsman_scores[striker.player_id]["out"] = True

        return {
            "total_runs": total_runs,
            "wickets": wickets,
            "overs": overs_bowled,
            "balls_bowled": balls_bowled,
            "run_rate": total_runs / max(overs_bowled, 0.1),
            "over_scores": over_scores,
            "batsman_scores": batsman_scores,
            "bowler_stats": bowler_stats,
            "target_achieved": target and total_runs >= target
        }

    def simulate_match(self, team1: Team, team2: Team, match_format: MatchFormat,
                      venue: str = "Neutral Venue", ai_predictor=None, on_ball=None) -> Match:
        """
        Simulate a complete cricket match.

        Args:
            team1: First team
            team2: Second team
            match_format: Format of the match
            venue: Match venue
            ai_predictor: Neural net model

        Returns:
            Completed Match object
        """
        import uuid
        from datetime import datetime

        match = Match(
            match_id=str(uuid.uuid4()),
            team1=team1,
            team2=team2,
            format=match_format,
            venue=venue,
            date=datetime.now().strftime("%Y-%m-%d")
        )

        # Simulate toss
        toss_winner = match.simulate_toss()

        # Decide who bats first based on toss and conditions
        if match.toss_decision == "bat":
            batting_first, bowling_first = toss_winner, team1 if toss_winner == team2 else team2
        else:
            bowling_first, batting_first = toss_winner, team1 if toss_winner == team2 else team2

        # First innings
        logger.info(f"{batting_first.name} batting first against {bowling_first.name}")
        first_innings = self.simulate_innings(batting_first, bowling_first, match, ai_predictor=ai_predictor, on_ball=on_ball)
        first_innings_score = first_innings["total_runs"]
        first_innings_wickets = first_innings["wickets"]
        first_innings_overs = first_innings["overs"]

        match.innings_scores.append({
            "innings": 1,
            "team": batting_first.name,
            "score": f"{first_innings_score}/{first_innings_wickets}",
            "overs": first_innings_overs,
            "run_rate": first_innings["run_rate"]
        })

        # Second innings (chase)
        logger.info(f"{bowling_first.name} chasing {first_innings_score + 1} against {batting_first.name}")
        second_innings = self.simulate_innings(bowling_first, batting_first, match, target=first_innings_score + 1, ai_predictor=ai_predictor, on_ball=on_ball)
        second_innings_score = second_innings["total_runs"]
        second_innings_wickets = second_innings["wickets"]
        second_innings_overs = second_innings["overs"]

        match.innings_scores.append({
            "innings": 2,
            "team": bowling_first.name,
            "score": f"{second_innings_score}/{second_innings_wickets}",
            "overs": second_innings_overs,
            "run_rate": second_innings["run_rate"]
        })

        # Determine winner
        if second_innings["target_achieved"]:
            match.winner = bowling_first
            match.result = f"{bowling_first.name} won by {10 - second_innings_wickets} wickets"
        elif second_innings_score > first_innings_score:
            match.winner = bowling_first
            match.result = f"{bowling_first.name} won by {second_innings_score - first_innings_score} runs"
        elif first_innings_score > second_innings_score:
            match.winner = batting_first
            match.result = f"{batting_first.name} won by {first_innings_score - second_innings_score} runs"
        else:
            match.result = "Match tied"

        return match


# Simple logger for the simulator
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)