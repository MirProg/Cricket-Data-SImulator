import numpy as np
import json
import os

class MarkovSimulator:
    def __init__(self, n_simulations=10000):
        self.n_simulations = n_simulations
        self._load_matrices()
        
    def _load_matrices(self):
        json_path = os.path.join(os.path.dirname(__file__), '../data/t20_transitions.json')
        
        # Fallback probabilities if JSON is missing
        default_probs = [0.33, 0.40, 0.06, 0.005, 0.11, 0.045, 0.05]
        self.outcomes = np.array([0, 1, 2, 3, 4, 6, -1])  # -1 represents a wicket
        
        self.matrices = {
            "powerplay": np.array(default_probs),
            "middle": np.array(default_probs),
            "death": np.array(default_probs)
        }
        
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                data = json.load(f)
                
            for phase in ["powerplay", "middle", "death"]:
                if phase in data:
                    probs_dict = data[phase]
                    # Map the dict back to our outcomes array
                    probs = [probs_dict.get(str(k), 0.0) for k in self.outcomes]
                    self.matrices[phase] = np.array(probs)
                    
    def get_phase_probs(self, balls_remaining):
        # T20 has 120 balls total.
        # Powerplay: Overs 1-6 -> balls 1-36 -> balls_remaining > 84
        # Middle: Overs 7-15 -> balls 37-90 -> balls_remaining > 30 and <= 84
        # Death: Overs 16-20 -> balls 91-120 -> balls_remaining <= 30
        if balls_remaining > 84:
            return self.matrices["powerplay"]
        elif balls_remaining > 30:
            return self.matrices["middle"]
        else:
            return self.matrices["death"]
            
    def simulate_innings(self, starting_runs, starting_balls_remaining, starting_wickets, prob_matrix=None):
        """
        Vectorized Monte Carlo simulation using NumPy for maximum performance.
        Now dynamically shifts phase matrices.
        """
        # MDP State Variables for parallel universes
        runs = np.full(self.n_simulations, starting_runs, dtype=np.int32)
        balls_remaining = np.full(self.n_simulations, starting_balls_remaining, dtype=np.int32)
        wickets_lost = np.full(self.n_simulations, starting_wickets, dtype=np.int32)
        
        max_balls = starting_balls_remaining
        
        # History arrays to track trajectories
        over_runs_history = np.zeros((self.n_simulations, max_balls // 6 + 1), dtype=np.int32)
        over_runs_history[:, 0] = runs
        
        rng = np.random.default_rng()
        
        for ball in range(max_balls):
            # Active simulations are those where balls > 0 and wickets < 10
            active_mask = (balls_remaining > 0) & (wickets_lost < 10)
            
            if not np.any(active_mask):
                break
                
            n_active = np.sum(active_mask)
            
            # Dynamically determine the phase probability based on balls remaining
            current_balls = np.max(balls_remaining[active_mask])
            current_probs = self.get_phase_probs(current_balls)
            
            # Sample outcomes for active simulations using the current probability matrix
            sampled_outcomes = rng.choice(self.outcomes, size=n_active, p=current_probs)
            
            # Update state based on outcomes
            # Wickets
            is_wicket = (sampled_outcomes == -1)
            wickets_lost[active_mask] += is_wicket
            
            # Runs
            runs_scored = np.where(is_wicket, 0, sampled_outcomes)
            runs[active_mask] += runs_scored
            
            # Balls
            balls_remaining[active_mask] -= 1
            
            # Save end-of-over snapshot
            if (max_balls - ball) % 6 == 0:
                over_idx = (max_balls - ball) // 6
                # Store runs at end of this over
                over_runs_history[:, (max_balls // 6) - over_idx + 1] = runs
                
        # Return summary statistics
        return {
            "mean_runs": float(np.mean(runs)),
            "median_runs": float(np.median(runs)),
            "p25_runs": float(np.percentile(runs, 25)),
            "p75_runs": float(np.percentile(runs, 75)),
            "p90_runs": float(np.percentile(runs, 90)),
            "mean_wickets": float(np.mean(wickets_lost)),
            "trajectories": over_runs_history[:100].tolist() # Return 100 sample paths for UI plotting
        }
