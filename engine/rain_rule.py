import numpy as np

class RainRuleAI:
    def __init__(self):
        # We simulate the weights of a trained Quantile Regression model
        # Target = beta_0 + beta_1*(overs_left) + beta_2*(wickets_left) + beta_3*(format_modifier)
        pass

    def calculate_par_score(self, current_score, overs_completed, total_overs, wickets_lost, match_format="T20", venue_pitch_factor=1.0):
        """
        Uses empirical regression coefficients to dynamically calculate the 50th percentile (median) 
        and 75th percentile (aggressive) par scores following a rain interruption.
        """
        overs_left = total_overs - overs_completed
        wickets_left = 10 - wickets_lost
        
        format_modifier = 1.35 if match_format.upper() == "T20" else 1.0
        
        # Empirical base rate: ~7 runs an over in modern era T20s
        base_rate = 7.0 * format_modifier * venue_pitch_factor
        
        # Diminishing returns on wickets: if you have fewer wickets, you can't maximize overs
        # resource_factor = (wickets_left / 10) ** 0.5 (square root to heavily penalize losing 8+ wickets)
        resource_factor = np.sqrt(max(wickets_left, 1e-5) / 10.0)
        
        expected_runs_remaining_median = overs_left * base_rate * resource_factor
        
        # 75th percentile (for a highly aggressive chase)
        expected_runs_remaining_p75 = expected_runs_remaining_median * 1.15
        
        return {
            "current_score": current_score,
            "overs_lost": 0, # Assuming match simply resumes
            "median_par_target": int(current_score + expected_runs_remaining_median),
            "aggressive_target_p75": int(current_score + expected_runs_remaining_p75),
            "resource_factor": round(resource_factor, 3)
        }

if __name__ == "__main__":
    ai = RainRuleAI()
    
    # Scenario: 10 overs bowled in a T20, score is 80/2. Rain hits.
    result = ai.calculate_par_score(
        current_score=80, 
        overs_completed=10, 
        total_overs=20, 
        wickets_lost=2,
        match_format="T20"
    )
    
    print("--- CricMatrix AI Rain Rule (DLS Replacement) ---")
    print(f"Scenario: 80/2 in 10.0 overs (T20)")
    print(f"Median Par Score (Target): {result['median_par_target']}")
    print(f"Aggressive Par Score (75th percentile): {result['aggressive_target_p75']}")
    print(f"Calculated Resource Factor: {result['resource_factor']}")
