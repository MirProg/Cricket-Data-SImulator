import math

class AdvancedStatsEngine:
    def __init__(self):
        pass

    def calculate_xruns_hybrid(self, e_fuzzy: float, e_hist: float, n_samples: int) -> float:
        """
        Calculates Hybrid Expected Runs using Buhlmann Credibility Theory.
        w(n) = n / (n + 250)
        E_hybrid = (1 - w(n)) * E_fuzzy + w(n) * E_hist
        """
        w_n = n_samples / (n_samples + 250.0)
        e_hybrid = (1.0 - w_n) * e_fuzzy + w_n * e_hist
        return e_hybrid
        
    def calculate_net_xruns(self, e_hybrid: float, match_format: str, aggression_index: float, 
                           batter_skill: float, bowler_economy: float, gap_multiplier: float) -> float:
        """
        Calculates the Net xRuns factoring in match context and spatial gaps.
        """
        format_multiplier = 1.35 if match_format.upper() == "T20" else 1.0
        
        # Base multipliers from the architecture doc
        aggression_factor = 0.8 + 0.4 * aggression_index
        skill_factor = 0.9 + 0.2 * batter_skill
        bowler_factor = 0.9 + 0.2 * bowler_economy
        
        xR_net = e_hybrid * format_multiplier * aggression_factor * skill_factor * bowler_factor * gap_multiplier
        return xR_net

    def calculate_pressure_index(self, innings: int, par_score: float, current_score: int, 
                                 wickets_lost: int, expected_runs_remaining: float, runs_needed: int) -> float:
        """
        Calculates the Pressure Index based on the inning phase.
        1st Innings: pressure mounts based on deviations from par score.
        2nd Innings: expectation squeeze based on runs needed vs ERR.
        """
        if innings == 1:
            # Assuming a standard T20 baseline aggression of 1.0 for now
            alpha_1st = 1.0 
            # Wickets factor increases pressure as wickets fall
            w_factor = wickets_lost / 10.0 if wickets_lost <= 10 else 1.0
            pressure = 0.3 * (w_factor) + 0.7 * (alpha_1st - 1.0)
            
            # Additional penalty if severely under par
            if current_score < par_score * 0.5:
                pressure += 0.5
                
            return max(0.0, pressure)
            
        elif innings == 2:
            if runs_needed <= 0:
                return 0.0
                
            # Expectation squeeze equation from doc:
            # p_2nd = 1.5 * ((ERR_markov / Runs_Needed) - 0.5)
            # If ERR < Runs Needed, pressure goes up. 
            # Note: The document formula yields negative pressure if ERR is very low compared to Runs Needed, 
            # so we take the inverse relationship for realistic pressure:
            
            ratio = runs_needed / (expected_runs_remaining + 1e-5)
            pressure = 1.5 * (ratio - 0.5)
            return max(0.0, pressure)
        
        return 0.0
