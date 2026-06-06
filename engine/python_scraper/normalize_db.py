import sqlite3
import os
import re

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "master_archive.sqlite"))

def main():
    print("Connecting to database...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Alter Schema
    try:
        cursor.execute("ALTER TABLE ScrapedMatches ADD COLUMN match_category TEXT")
        cursor.execute("ALTER TABLE ScrapedMatches ADD COLUMN match_format TEXT")
        cursor.execute("ALTER TABLE ScrapedMatches ADD COLUMN match_country TEXT")
        print("Added new columns to ScrapedMatches.")
    except sqlite3.OperationalError:
        print("Columns already exist, proceeding to update...")

    # 2. Fetch Data
    print("Fetching matches...")
    cursor.execute("SELECT match_id, title, series, venue, format FROM ScrapedMatches")
    matches = cursor.fetchall()
    
    updates = []
    
    countries = ["England", "Australia", "India", "South Africa", "New Zealand", "West Indies", "Pakistan", "Sri Lanka", "Bangladesh", "Zimbabwe", "Ireland", "Afghanistan"]

    print(f"Normalizing {len(matches)} matches...")
    for m_id, title, series, venue, old_format in matches:
        format_str = ""
        category_str = ""
        country_str = ""
        
        # Determine Country
        full_text = f"{title} {series} {venue}".lower()
        for c in countries:
            if f"in {c.lower()}" in full_text or f", {c.lower()}" in full_text:
                country_str = c
                break
        
        # Determine Format
        # Priority 1: Check old format column if it was populated
        if old_format and len(old_format) > 1:
            if 'Test' in old_format: format_str = 'Test'
            elif 'ODI' in old_format: format_str = 'ODI'
            elif 'T20I' in old_format: format_str = 'T20I'
            elif 'T20' in old_format: format_str = 'T20'
            elif 'List A' in old_format: format_str = 'List A'
            elif 'First-Class' in old_format: format_str = 'First-Class'
        
        # Priority 2: Check series
        if not format_str and series:
            s_lower = series.lower()
            if 'test' in s_lower: format_str = 'Test'
            elif 'odi' in s_lower or 'one-day international' in s_lower: format_str = 'ODI'
            elif 't20i' in s_lower: format_str = 'T20I'
            elif 'first-class' in s_lower: format_str = 'First-Class'
            elif 'list a' in s_lower or '1-day match' in s_lower or '1-day single innings' in s_lower: format_str = 'List A'
            elif 't20' in s_lower or '20-over match' in s_lower: format_str = 'T20'
            
        # Priority 3: Check venue (modern scraper hides it here)
        if not format_str and venue:
            match = re.search(r'\((.*?)\)', venue)
            if match:
                inner = match.group(1).lower()
                if 'test' in inner: format_str = 'Test'
                elif 'odi' in inner: format_str = 'ODI'
                elif 't20i' in inner: format_str = 'T20I'
                elif '20-over' in inner or 't20' in inner: format_str = 'T20'
                elif '50-over' in inner or 'list a' in inner or '40-over' in inner or '45-over' in inner or '1-day' in inner: format_str = 'List A'
                elif 'first-class' in inner or '3-day' in inner or '4-day' in inner: format_str = 'First-Class'
                
        if not format_str:
            format_str = 'Other'
            
        # Determine Category
        if format_str in ['Test', 'ODI', 'T20I']:
            category_str = 'International'
        elif format_str in ['First-Class', 'List A', 'T20']:
            category_str = 'Domestic'
        else:
            category_str = 'Other'
            
        updates.append((category_str, format_str, country_str, m_id))

    # 3. Batch Update
    print("Writing updates to SQLite...")
    cursor.executemany("UPDATE ScrapedMatches SET match_category = ?, match_format = ?, match_country = ? WHERE match_id = ?", updates)
    conn.commit()
    conn.close()
    print("Database Normalization Complete!")

if __name__ == "__main__":
    main()
