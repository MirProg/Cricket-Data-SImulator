import sqlite3
import uuid
from rapidfuzz import fuzz, process

DB_PATH = "data/cricmatrix.db"

class EntityResolver:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS canonical_players (
                    canonical_id TEXT PRIMARY KEY,
                    primary_name TEXT,
                    nationality TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS player_aliases (
                    raw_name TEXT PRIMARY KEY,
                    source TEXT,
                    canonical_id TEXT,
                    FOREIGN KEY(canonical_id) REFERENCES canonical_players(canonical_id)
                )
            """)

    def resolve_entities(self, similarity_threshold=85):
        print("[*] Starting Entity Resolution pipeline...")
        with sqlite3.connect(self.db_path) as conn:
            # We assume a raw_players table exists. 
            # If it doesn't, we'll mock some raw names for demonstration.
            try:
                cursor = conn.execute("SELECT name, source FROM raw_players")
                raw_records = cursor.fetchall()
            except sqlite3.OperationalError:
                print("[!] 'raw_players' table not found. Creating mock dataset for Phase 3 MVP...")
                raw_records = [
                    ("Virat Kohli", "cricsheet"),
                    ("V. Kohli", "cricbuzz"),
                    ("Kohli, V", "cricketarchive"),
                    ("Sachin Tendulkar", "cricsheet"),
                    ("S. Tendulkar", "cricketarchive"),
                    ("MS Dhoni", "cricsheet"),
                    ("Mahendra Singh Dhoni", "cricbuzz"),
                    ("S Curran", "cricsheet"),
                    ("Sam Curran", "cricbuzz"),
                    ("Tom Curran", "cricbuzz") # Should NOT cluster with Sam Curran
                ]
            
            canonical_clusters = {}
            aliases_mapping = []

            for raw_name, source in raw_records:
                matched = False
                
                # Check against existing clusters
                if canonical_clusters:
                    existing_names = list(canonical_clusters.keys())
                    # Using token_sort_ratio handles "Kohli, V" and "V. Kohli" well
                    best_match = process.extractOne(
                        raw_name, 
                        existing_names, 
                        scorer=fuzz.token_sort_ratio
                    )
                    
                    if best_match and best_match[1] >= similarity_threshold:
                        # Found a match!
                        cluster_key = best_match[0]
                        canonical_id = canonical_clusters[cluster_key]
                        aliases_mapping.append((raw_name, source, canonical_id))
                        matched = True
                
                if not matched:
                    # Create new canonical cluster
                    new_canonical_id = str(uuid.uuid4())
                    # Use the first encountered name as the primary name
                    canonical_clusters[raw_name] = new_canonical_id
                    aliases_mapping.append((raw_name, source, new_canonical_id))

            # Insert to DB
            for primary_name, can_id in canonical_clusters.items():
                conn.execute(
                    "INSERT OR IGNORE INTO canonical_players (canonical_id, primary_name) VALUES (?, ?)",
                    (can_id, primary_name)
                )
            
            for raw_name, source, can_id in aliases_mapping:
                conn.execute(
                    "INSERT OR REPLACE INTO player_aliases (raw_name, source, canonical_id) VALUES (?, ?, ?)",
                    (raw_name, source, can_id)
                )
            
            print(f"[+] Successfully clustered {len(raw_records)} raw records into {len(canonical_clusters)} unique canonical players.")

if __name__ == "__main__":
    resolver = EntityResolver()
    resolver.resolve_entities()
