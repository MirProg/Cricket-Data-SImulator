from bs4 import BeautifulSoup

with open("ca_test.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "lxml")
tables = soup.find_all("table")

print(f"Found {len(tables)} tables")

for i, table in enumerate(tables):
    rows = table.find_all("tr")
    if not rows: continue
    
    first_row_text = rows[0].get_text(strip=True).lower()
    
    # Check if it's a batting table (e.g., "batsman", "runs", "mins")
    if "runs" in first_row_text and "mins" in first_row_text and "balls" in first_row_text:
        print(f"\n--- Table {i} looks like BATTING ---")
        for row in rows[:5]:
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            print(cells)
            
    # Check if it's a bowling table (e.g., "bowler", "overs", "maidens", "runs", "wickets")
    else:
        print(f"\n--- Table {i} ---")
        for row in rows[:2]:
            print([c.get_text(strip=True) for c in row.find_all(["td", "th"])])
