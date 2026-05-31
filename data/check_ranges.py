import sqlite3

conn = sqlite3.connect('data/cricket_db.sqlite')
c = conn.cursor()

for status in ['PENDING', 'COMPLETED', 'FAILED']:
    c.execute(f"SELECT MIN(ca_match_id), MAX(ca_match_id) FROM CrawlQueue WHERE status=?", (status,))
    row = c.fetchone()
    print(f"{status}: min={row[0]}, max={row[1]}")

# Show distribution of pending IDs in buckets of 10000
print("\nPending ID distribution (buckets of 10000):")
c.execute("""
    SELECT (ca_match_id / 10000) * 10000 as bucket, COUNT(1) as cnt
    FROM CrawlQueue WHERE status='PENDING'
    GROUP BY bucket ORDER BY bucket
""")
for row in c.fetchall():
    print(f"  {row[0]}-{row[0]+9999}: {row[1]}")

conn.close()
