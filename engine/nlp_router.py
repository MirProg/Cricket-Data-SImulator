import re

class NLPRouter:
    def __init__(self):
        # A simple list of known countries to help with entity extraction
        self.known_teams = [
            "india", "australia", "england", "pakistan", "south africa",
            "new zealand", "sri lanka", "west indies", "bangladesh",
            "zimbabwe", "afghanistan", "ireland", "netherlands", "scotland"
        ]

    def parse_query(self, query: str):
        query = query.lower()
        payload = {
            "mode": "batting",
            "filters": {}
        }
        
        # Determine Mode
        if any(w in query for w in ["wickets", "bowling", "economy", "five", "fifer", "best bowling"]):
            payload["mode"] = "bowling"
        
        # Determine Format
        if "test" in query:
            payload["filters"]["format"] = "Test"
        elif "odi" in query or "one day" in query:
            payload["filters"]["format"] = "ODI"
        elif "t20" in query or "twenty20" in query:
            payload["filters"]["format"] = "T20"
            
        # Determine Match Result (Win Contribution)
        if any(w in query for w in ["win", "won", "wins", "victories"]):
            payload["filters"]["match_result"] = "won"
        elif any(w in query for w in ["loss", "lost", "defeats"]):
            payload["filters"]["match_result"] = "lost"
        elif any(w in query for w in ["draw", "drawn"]):
            payload["filters"]["match_result"] = "drawn"
            
        # Determine Year
        year_match = re.search(r'\b(19|20)\d{2}\b', query)
        if year_match:
            payload["filters"]["year"] = year_match.group(0)
            
        # Determine Team and Opposition
        # Simple heuristics: "for [team]" or "in [team] wins"
        for team in self.known_teams:
            if f"for {team}" in query or f" {team} wins" in query or f" {team} won" in query:
                payload["filters"]["team"] = team.title()
                
            if f"against {team}" in query or f"vs {team}" in query:
                payload["filters"]["opposition"] = team.title()

        # If a team is mentioned but no 'for' or 'against', assign to team if empty, else opposition
        if "team" not in payload["filters"] and "opposition" not in payload["filters"]:
            for team in self.known_teams:
                if team in query:
                    if "team" not in payload["filters"]:
                        payload["filters"]["team"] = team.title()
                    elif payload["filters"]["team"].lower() != team:
                        payload["filters"]["opposition"] = team.title()
                        
        # Extract Player vs Player matchup
        # "dismissed by [bowler]" or "against [bowler]" (rough heuristic)
        by_match = re.search(r'(?:dismissed by|against bowler) ([a-z ]+)', query)
        if by_match:
            bowler = by_match.group(1).strip()
            # Remove filler words
            for filler in ["in", "the", "a", "an"]:
                if bowler.endswith(f" {filler}"):
                    bowler = bowler[:-len(filler)-1]
            payload["filters"]["bowler_name"] = bowler.title()

        return payload
