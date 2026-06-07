import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "master_archive.sqlite")

class StatsguruEngine:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    def _apply_common_filters(self, filters, where_clauses, params, is_batting=True):
        if filters.get("team"):
            where_clauses.append("(m.team1 LIKE ? OR m.team2 LIKE ?)")
            params.extend([f"%{filters['team']}%", f"%{filters['team']}%"])
            
        if filters.get("opposition"):
            where_clauses.append("(m.team1 LIKE ? OR m.team2 LIKE ?)")
            params.extend([f"%{filters['opposition']}%", f"%{filters['opposition']}%"])
            
        if filters.get("ground"):
            where_clauses.append("m.ground_name LIKE ?")
            params.append(f"%{filters['ground']}%")
            
        if filters.get("format"):
            where_clauses.append("m.match_format LIKE ?")
            params.append(f"%{filters['format']}%")
            
        if filters.get("year"):
            where_clauses.append("m.season LIKE ?")
            params.append(f"%{filters['year']}%")

        if filters.get("match_result"):
            res = filters['match_result'].lower()
            if res == "won" and filters.get("team"):
                where_clauses.append("lower(m.result) LIKE ?")
                params.append(f"%{filters['team'].lower()} won%")
            elif res == "lost" and filters.get("team"):
                where_clauses.append("lower(m.result) NOT LIKE ? AND lower(m.result) LIKE '%won%'")
                params.append(f"%{filters['team'].lower()} won%")
            elif res == "drawn" or res == "draw":
                where_clauses.append("lower(m.result) LIKE '%drawn%'")

        if is_batting and filters.get("bowler_name"):
            where_clauses.append("lower(b.dismissal) LIKE ?")
            params.append(f"%b {filters['bowler_name'].lower()}%")

    def build_batting_query(self, filters):
        base_select = """
            SELECT 
                b.player_name,
                COUNT(DISTINCT b.match_id) as matches,
                COUNT(b.id) as innings,
                SUM(CASE WHEN lower(b.dismissal) LIKE '%not out%' OR lower(b.dismissal) LIKE '%retired hurt%' THEN 1 ELSE 0 END) as not_outs,
                SUM(b.runs) as total_runs,
                SUM(CAST(b.balls AS INTEGER)) as balls_faced,
                MAX(b.runs) as highest_score,
                SUM(CASE WHEN b.runs >= 100 THEN 1 ELSE 0 END) as hundreds,
                SUM(CASE WHEN b.runs >= 50 AND b.runs < 100 THEN 1 ELSE 0 END) as fifties,
                SUM(CASE WHEN b.runs = 0 AND lower(b.dismissal) NOT LIKE '%not out%' AND lower(b.dismissal) NOT LIKE '%retired hurt%' THEN 1 ELSE 0 END) as ducks
            FROM ScrapedBatting b
            JOIN ScrapedMatches m ON b.match_id = m.match_id
        """
        where_clauses = []
        params = []
        
        if filters.get("player_name"):
            where_clauses.append("b.player_name LIKE ?")
            params.append(f"%{filters['player_name']}%")
            
        self._apply_common_filters(filters, where_clauses, params, is_batting=True)

        sql = base_select
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
            
        sql += " GROUP BY b.player_name HAVING innings > 0 ORDER BY total_runs DESC LIMIT 50"
        return sql, params

    def build_bowling_query(self, filters):
        base_select = """
            SELECT 
                bw.player_name,
                COUNT(DISTINCT bw.match_id) as matches,
                COUNT(bw.id) as innings,
                SUM(bw.wickets) as total_wickets,
                SUM(bw.runs) as runs_conceded,
                SUM(CAST(bw.overs AS FLOAT)) as overs_bowled,
                SUM(CAST(bw.maidens AS INTEGER)) as maidens,
                MAX(bw.wickets) as best_wickets,
                SUM(CASE WHEN bw.wickets >= 5 THEN 1 ELSE 0 END) as five_wicket_hauls
            FROM ScrapedBowling bw
            JOIN ScrapedMatches m ON bw.match_id = m.match_id
        """
        where_clauses = []
        params = []
        
        if filters.get("player_name"):
            where_clauses.append("bw.player_name LIKE ?")
            params.append(f"%{filters['player_name']}%")
            
        self._apply_common_filters(filters, where_clauses, params, is_batting=False)

        sql = base_select
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
            
        sql += " GROUP BY bw.player_name HAVING innings > 0 ORDER BY total_wickets DESC LIMIT 50"
        return sql, params

    def execute_query(self, mode, filters):
        if mode == "batting":
            sql, params = self.build_batting_query(filters)
        elif mode == "bowling":
            sql, params = self.build_bowling_query(filters)
        else:
            raise ValueError("Invalid mode")

        results = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(sql, params)
                columns = [col[0] for col in cursor.description]
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    if mode == "batting":
                        outs = row_dict['innings'] - row_dict['not_outs']
                        row_dict['average'] = round(row_dict['total_runs'] / outs, 2) if outs > 0 else None
                        row_dict['strike_rate'] = round((row_dict['total_runs'] / row_dict['balls_faced']) * 100, 2) if row_dict['balls_faced'] > 0 else None
                    elif mode == "bowling":
                        overs = row_dict['overs_bowled']
                        wickets = row_dict['total_wickets']
                        runs = row_dict['runs_conceded']
                        row_dict['bowling_average'] = round(runs / wickets, 2) if wickets > 0 else None
                        row_dict['economy'] = round(runs / overs, 2) if overs > 0 else None
                    results.append(row_dict)
        except Exception as e:
            return {"error": str(e), "sql": sql}
            
        return {"sql": sql, "count": len(results), "data": results}
