import sqlite3
import uuid

OLD_DB = "data/cricket_db.sqlite"
NEW_DB = "D:/cricket_data/cricmatrix.db"

def unify_data():
    print("[*] Connecting to databases...")
    old_conn = sqlite3.connect(OLD_DB)
    new_conn = sqlite3.connect(NEW_DB)
    
    print("[*] Migrating CricketArchive Deliveries...")
    # Select first 500k deliveries to prevent memory issues during rapid prototyping. 
    # In production, we chunk this.
    chunk_size = 500000
    # Start offset from where we crashed last time (2,038,755)
    offset = 2038755
    total_migrated = offset
    
    while True:
        ca_deliveries = old_conn.execute(f"SELECT * FROM BallByBall LIMIT {chunk_size} OFFSET {offset}").fetchall()
        if not ca_deliveries:
            break
            
        deliveries_to_insert = []
        for d in ca_deliveries:
            d_id = str(uuid.uuid4())
            m_id = f"ca_{d[1]}"
            r_tot = (d[8] or 0) + (d[9] or 0)
            deliveries_to_insert.append((
                d_id, m_id, d[2], d[3], d[4], d[5], d[6], d[7], d[8], d[9], r_tot, d[10], d[11], d[12]
            ))
            
        try:
            new_conn.executemany("""
                INSERT OR IGNORE INTO deliveries
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, deliveries_to_insert)
            new_conn.commit()
            total_migrated += len(deliveries_to_insert)
            print(f"[+] Migrated {total_migrated} deliveries...")
        except Exception as e:
            print(f"[!] Error migrating deliveries: {e}")
            break
            
        offset += chunk_size

    print("[+] Migration Complete!")
    old_conn.close()
    new_conn.close()

if __name__ == "__main__":
    unify_data()
