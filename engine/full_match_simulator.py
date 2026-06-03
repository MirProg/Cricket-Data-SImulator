import json
import os
import random
import numpy as np
from pathlib import Path

class FullMatchSimulator:
    def __init__(self):
        # Load empirical T20 phase matrix (Phase 8)
        transitions_path = os.path.join(os.path.dirname(__file__), "..", "data", "t20_transitions.json")
        stats_path = os.path.join(os.path.dirname(__file__), "..", "data", "player_stats.json")
        
        with open(transitions_path, 'r') as f:
            self.base_matrix = json.load(f)
            
        with open(stats_path, 'r') as f:
            self.player_stats = json.load(f)
            
        # Baseline T20 stats used to calculate relative modifiers
        self.BASELINE_SR = 125.0
        self.BASELINE_AVG = 22.0
        self.BASELINE_ECON = 7.5
        self.BASELINE_BSR = 18.0
        
    def _get_phase(self, over):
        if over < 6: return "powerplay"
        if over < 15: return "middle"
        return "death"

    def _get_player_stat(self, name, stat_type, default):
        if name in self.player_stats and stat_type in self.player_stats[name]:
            return self.player_stats[name][stat_type]
        return default

    def _get_ball_outcome(self, striker, bowler, over):
        phase = self._get_phase(over)
        base_probs = self.base_matrix[phase]
        
        b_sr = self._get_player_stat(striker, "batting_sr", self.BASELINE_SR)
        b_avg = self._get_player_stat(striker, "batting_avg", self.BASELINE_AVG)
        bowl_econ = self._get_player_stat(bowler, "bowling_econ", self.BASELINE_ECON)
        bowl_sr = self._get_player_stat(bowler, "bowling_sr", self.BASELINE_BSR)
        
        # Adjust boundary probabilities (4s and 6s)
        # Better batter SR -> higher boundaries. Worse bowler econ -> higher boundaries
        aggression_factor = (b_sr / self.BASELINE_SR) * (bowl_econ / self.BASELINE_ECON)
        
        # Adjust wicket probabilities
        # Better bowler SR (lower) -> higher wicket. Better batter Avg (higher) -> lower wicket
        survival_factor = (self.BASELINE_BSR / bowl_sr) * (self.BASELINE_AVG / b_avg)
        
        outcomes = ["0", "1", "2", "3", "4", "6", "W"]
        probs = []
        
        for out in outcomes:
            p = base_probs.get(out, 0.0)
            if out in ["4", "6"]:
                p *= aggression_factor
            elif out == "W":
                p *= survival_factor
            # Dots and 1s get slightly suppressed if aggression is high
            elif out in ["0", "1"] and aggression_factor > 1.0:
                p *= (1.0 / aggression_factor)
            probs.append(p)
            
        # Normalize
        total_p = sum(probs)
        probs = [p / total_p for p in probs]
        
        # Sample
        result = np.random.choice(outcomes, p=probs)
        return result

    def simulate_innings(self, batting_team, bowling_team, target=None):
        runs = 0
        wickets = 0
        balls = 0
        
        scorecard = {
            "batting": {p: {"runs": 0, "balls": 0, "4s": 0, "6s": 0, "out": False, "bowler": None} for p in batting_team},
            "bowling": {p: {"overs": 0.0, "runs": 0, "wickets": 0, "balls": 0} for p in bowling_team},
            "timeline": [],
            "fall_of_wickets": []
        }
        
        striker_idx = 0
        non_striker_idx = 1
        next_batter_idx = 2
        
        # Simple bowler rotation (5 bowlers bowling 4 overs each)
        for over in range(20):
            bowler = bowling_team[over % len(bowling_team)]
            
            for ball in range(6):
                if wickets == 10: break
                if target is not None and runs >= target: break
                
                striker = batting_team[striker_idx]
                outcome = self._get_ball_outcome(striker, bowler, over)
                balls += 1
                
                scorecard["batting"][striker]["balls"] += 1
                scorecard["bowling"][bowler]["balls"] += 1
                
                if outcome == "W":
                    wickets += 1
                    scorecard["batting"][striker]["out"] = True
                    scorecard["batting"][striker]["bowler"] = bowler
                    scorecard["bowling"][bowler]["wickets"] += 1
                    scorecard["fall_of_wickets"].append(f"{runs}/{wickets} ({striker}, {over}.{ball+1} ov)")
                    
                    scorecard["timeline"].append(f"{over}.{ball+1} {bowler} to {striker}: OUT!")
                    
                    if wickets < 10:
                        striker_idx = next_batter_idx
                        next_batter_idx += 1
                else:
                    r = int(outcome)
                    runs += r
                    scorecard["batting"][striker]["runs"] += r
                    scorecard["bowling"][bowler]["runs"] += r
                    
                    if r == 4: scorecard["batting"][striker]["4s"] += 1
                    if r == 6: scorecard["batting"][striker]["6s"] += 1
                    
                    scorecard["timeline"].append(f"{over}.{ball+1} {bowler} to {striker}: {r} runs")
                    
                    # Rotate strike on odd runs
                    if r % 2 != 0:
                        striker_idx, non_striker_idx = non_striker_idx, striker_idx
                        
            # Rotate strike at end of over
            striker_idx, non_striker_idx = non_striker_idx, striker_idx
            # Calculate full overs for bowler
            scorecard["bowling"][bowler]["overs"] = scorecard["bowling"][bowler]["balls"] // 6 + (scorecard["bowling"][bowler]["balls"] % 6) / 10.0
            
            if wickets == 10 or (target is not None and runs >= target):
                break
                
        return {
            "total_runs": runs,
            "total_wickets": wickets,
            "overs": balls // 6 + (balls % 6) / 10.0,
            "scorecard": scorecard
        }

    def simulate_match(self, team1_lineup, team2_lineup):
        # We assume first 5 players in team2 are bowlers for simplicity in MVP
        t2_bowlers = team2_lineup[-5:] if len(team2_lineup) >= 5 else team2_lineup
        inn1 = self.simulate_innings(team1_lineup, t2_bowlers)
        
        t1_bowlers = team1_lineup[-5:] if len(team1_lineup) >= 5 else team1_lineup
        inn2 = self.simulate_innings(team2_lineup, t1_bowlers, target=inn1["total_runs"] + 1)
        
        winner = "Team 1" if inn1["total_runs"] > inn2["total_runs"] else "Team 2"
        if inn1["total_runs"] == inn2["total_runs"]: winner = "Tie"
        
        return {
            "team1_innings": inn1,
            "team2_innings": inn2,
            "winner": winner
        }
