import sqlite3
import json
import os

DB_PATH = 'D:/cricket_data/cricmatrix.db'
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '../data/t20_transitions.json')

def build_t20_matrices():
    print(f"Connecting to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # We will compute the probabilities for the following outcomes: 0, 1, 2, 3, 4, 6, Wicket (-1)
    # Grouped by phase:
    # Powerplay: Overs 0 to 5
    # Middle: Overs 6 to 14
    # Death: Overs 15 to 19

    phases = {
        "powerplay": "d.over >= 0 AND d.over <= 5",
        "middle": "d.over >= 6 AND d.over <= 14",
        "death": "d.over >= 15 AND d.over <= 19"
    }
    
    matrices = {}
    
    for phase_name, condition in phases.items():
        print(f"Calculating probabilities for {phase_name}...")
        
        # Query to count outcomes
        query = f"""
            SELECT 
                CASE 
                    WHEN d.is_wicket = 1 THEN -1
                    ELSE d.runs_batter
                END as outcome,
                COUNT(*) as count
            FROM deliveries d
            JOIN matches m ON d.match_id = m.match_id
            WHERE m.format = 'T20' AND ({condition})
            GROUP BY outcome
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Calculate probabilities
        total_deliveries = sum([row[1] for row in results])
        print(f"Total deliveries in {phase_name}: {total_deliveries}")
        
        if total_deliveries == 0:
            print(f"Warning: No deliveries found for {phase_name}")
            matrices[phase_name] = {str(k): 0 for k in [-1, 0, 1, 2, 3, 4, 6]}
            continue
            
        prob_map = {row[0]: row[1] / total_deliveries for row in results}
        
        # Ensure all required outcomes are present (0, 1, 2, 3, 4, 6, -1)
        required_outcomes = [-1, 0, 1, 2, 3, 4, 6]
        final_probs = {}
        for outcome in required_outcomes:
            final_probs[str(outcome)] = prob_map.get(outcome, 0.0)
            
        # Normalize just in case (excluding weird outcomes like 5 runs or 7 runs)
        prob_sum = sum(final_probs.values())
        if prob_sum > 0:
            for k in final_probs:
                final_probs[k] /= prob_sum
                
        matrices[phase_name] = final_probs
        
    print(f"Writing results to {OUTPUT_FILE}")
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(matrices, f, indent=4)
        
    print("Done!")

if __name__ == "__main__":
    build_t20_matrices()
