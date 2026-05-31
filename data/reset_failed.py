import sqlite3

conn = sqlite3.connect('data/cricket_db.sqlite')
c = conn.cursor()
c.execute("UPDATE CrawlQueue SET status='PENDING' WHERE status='FAILED'")
conn.commit()
print(f"Reset {c.rowcount} FAILED matches back to PENDING")
conn.close()
