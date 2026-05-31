import sqlite3

conn = sqlite3.connect('data/cricket_db.sqlite')
c = conn.cursor()

c.execute("SELECT COUNT(1) FROM CrawlQueue WHERE espn_match_id IS NOT NULL AND espn_match_id != ''")
print("ESPN IDs:", c.fetchone()[0])

c.execute("SELECT COUNT(1) FROM CrawlQueue WHERE cb_match_id IS NOT NULL AND cb_match_id != ''")
print("Cricbuzz IDs:", c.fetchone()[0])

c.execute("SELECT COUNT(1) FROM CrawlQueue WHERE ca_match_id IS NOT NULL AND ca_match_id != ''")
print("CricketArchive IDs:", c.fetchone()[0])

conn.close()
