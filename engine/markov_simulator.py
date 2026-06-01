import numpy as np

class MarkovSimulator:
    def __init__(self, n_simulations=10000):
        self.n_simulations = n_simulations
        
    def simulate_innings(self, starting_runs, starting_balls_remaining, starting_wickets, prob_matrix=None):
        """
        Vectorized Monte Carlo simulation using NumPy for maximum performance.
        prob_matrix: A dictionary or object that provides probability distribution
                     for outcomes (0, 1, 2, 3, 4, 6, Wicket) given the state.
        For Phase 2 MVP, we will use a generic T20 empirical probability matrix.
        """
        # MDP State Variables for 10,000 parallel universes
        runs = np.full(self.n_simulations, starting_runs, dtype=np.int32)
        balls_remaining = np.full(self.n_simulations, starting_balls_remaining, dtype=np.int32)
        wickets_lost = np.full(self.n_simulations, starting_wickets, dtype=np.int32)
        
        # Generic T20 baseline probabilities: [0, 1, 2, 3, 4, 6, Wicket]
        # Based on global empirical distribution: ~33% dots, ~40% singles, ~6% twos, ~0.5% threes, ~11% fours, ~4.5% sixes, ~5% wickets
        outcomes = np.array([0, 1, 2, 3, 4, 6, -1])  # -1 represents a wicket
        baseline_probs = np.array([0.33, 0.40, 0.06, 0.005, 0.11, 0.045, 0.05])
        
        # We loop over balls_remaining (max 120 for T20).
        # Inside the loop, all operations are vectorized over the 10,000 simulations.
        max_balls = starting_balls_remaining
        
        # History arrays to track trajectories (optional, but good for graphs)
        # We'll just track runs at the end of each over for graphing
        over_runs_history = np.zeros((self.n_simulations, max_balls // 6 + 1), dtype=np.int32)
        over_runs_history[:, 0] = runs
        
        rng = np.random.default_rng()
        
        for ball in range(max_balls):
            # Active simulations are those where balls > 0 and wickets < 10
            active_mask = (balls_remaining > 0) & (wickets_lost < 10)
            
            if not np.any(active_mask):
                break
                
            n_active = np.sum(active_mask)
            
            # Sample outcomes for active simulations using the probability matrix
            # In advanced phases, prob matrix dynamically shifts based on Phase dominance & batter/bowler match up
            sampled_outcomes = rng.choice(outcomes, size=n_active, p=baseline_probs)
            
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
