"""
Master Data Unification Engine
Merges CricketArchive, Cricsheet, Cricbuzz, and ESPN data into a single
deduplicated UnifiedMatchRegistry with fingerprint-based overlap detection.
"""
import sqlite3
import hashlib
import re
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SOURCE_DB = r"C:\Users\seo\.local\bin\cricket_simulator\data\cricket_db.sqlite"
TARGET_DB = r"C:\Users\seo\.local\bin\cricket_simulator\data\master_archive.sqlite"

# ============================================================
# TEAM NAME NORMALIZATION
# ============================================================
TEAM_ALIASES = {
    # International men's
    "aus": "Australia", "australia": "Australia",
    "ind": "India", "india": "India",
    "eng": "England", "england": "England",
    "pak": "Pakistan", "pakistan": "Pakistan",
    "sa": "South Africa", "south africa": "South Africa",
    "nz": "New Zealand", "new zealand": "New Zealand",
    "wi": "West Indies", "west indies": "West Indies",
    "sl": "Sri Lanka", "sri lanka": "Sri Lanka",
    "ban": "Bangladesh", "bangladesh": "Bangladesh",
    "zim": "Zimbabwe", "zimbabwe": "Zimbabwe",
    "afg": "Afghanistan", "afghanistan": "Afghanistan",
    "ire": "Ireland", "ireland": "Ireland",
    "sco": "Scotland", "scotland": "Scotland",
    "ned": "Netherlands", "netherlands": "Netherlands",
    "nam": "Namibia", "namibia": "Namibia",
    "uae": "United Arab Emirates", "united arab emirates": "United Arab Emirates",
    "usa": "United States of America", "united states of america": "United States of America",
    "nep": "Nepal", "nepal": "Nepal",
    "oman": "Oman",
    "png": "Papua New Guinea", "papua new guinea": "Papua New Guinea",
    # Women's
    "australia women": "Australia Women",
    "india women": "India Women",
    "england women": "England Women",
    "new zealand women": "New Zealand Women",
    "south africa women": "South Africa Women",
    "west indies women": "West Indies Women",
    "pakistan women": "Pakistan Women",
    "sri lanka women": "Sri Lanka Women",
    "bangladesh women": "Bangladesh Women",
    "ireland women": "Ireland Women",
}

MONTHS = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "jun": "06", "jul": "07", "aug": "08", "sep": "09",
    "oct": "10", "nov": "11", "dec": "12",
}


def normalize_team(name):
    """Normalize a team name to its canonical form."""
    if not name:
        return "Unknown"
    key = name.strip().lower()
    if key in TEAM_ALIASES:
        return TEAM_ALIASES[key]
    # Return as-is with title case if not in our aliases
    return name.strip()


def parse_fuzzy_date(date_str):
    """
    Parse various date formats into YYYY-MM-DD.
    Handles:
      - "2017-02-17" (ISO)
      - "17th July 2023" 
      - "8th December 2024"
      - "Aldridge Ground on 13th May 2023"
      - "22nd, 23rd June 1854"
    Returns the best-effort date string or "UNKNOWN".
    """
    if not date_str:
        return "UNKNOWN"

    # Already ISO format
    iso = re.match(r'^(\d{4})-(\d{2})-(\d{2})', date_str)
    if iso:
        return iso.group(0)

    # Extract year
    year_match = re.search(r'\b(1[6-9]\d{2}|20\d{2})\b', date_str)
    year = year_match.group(0) if year_match else "0000"

    # Extract month
    month = "00"
    for m_name, m_num in MONTHS.items():
        if m_name in date_str.lower():
            month = m_num
            break

    # Extract day (first number that looks like a day: 1-31, possibly with st/nd/rd/th)
    day_match = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\b', date_str)
    day = day_match.group(1).zfill(2) if day_match else "00"
    # Validate day is reasonable
    if day_match:
        d = int(day_match.group(1))
        if d < 1 or d > 31:
            day = "00"

    return f"{year}-{month}-{day}"


def generate_fingerprint(team1, team2, date_normalized, fmt):
    """
    Generate a unique fingerprint for a match.
    Teams are sorted alphabetically so "A vs B" == "B vs A".
    """
    t1 = normalize_team(team1)
    t2 = normalize_team(team2)
    teams = sorted([t1.lower(), t2.lower()])
    fmt_norm = (fmt or "unknown").lower().strip()
    key = f"{teams[0]}|{teams[1]}|{date_normalized}|{fmt_norm}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def ensure_unified_tables(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS UnifiedMatchRegistry (
            universal_id    TEXT PRIMARY KEY,
            team1           TEXT,
            team2           TEXT,
            match_date      TEXT,
            venue           TEXT,
            format          TEXT,
            ca_match_id     TEXT,
            cricsheet_id    TEXT,
            cricbuzz_id     TEXT,
            espn_id         TEXT,
            scraped_id      INTEGER,
            has_scorecard   BOOLEAN DEFAULT 0,
            has_ball_by_ball BOOLEAN DEFAULT 0,
            has_commentary  BOOLEAN DEFAULT 0,
            source_priority TEXT
        );
        CREATE TABLE IF NOT EXISTS TeamAliases (
            alias TEXT PRIMARY KEY,
            canonical_name TEXT
        );
    """)
    # Populate TeamAliases
    for alias, canonical in TEAM_ALIASES.items():
        conn.execute(
            "INSERT OR IGNORE INTO TeamAliases (alias, canonical_name) VALUES (?, ?)",
            (alias, canonical)
        )
    conn.commit()


def unify():
    src = sqlite3.connect(SOURCE_DB)
    tgt = sqlite3.connect(TARGET_DB)
    ensure_unified_tables(tgt)

    # Clear old registry
    tgt.execute("DELETE FROM UnifiedMatchRegistry")

    registry = {}  # fingerprint -> dict

    # ============================================================
    # SOURCE 1: CricketArchive (CAMatches)
    # ============================================================
    logging.info("Processing CricketArchive matches...")
    ca_rows = src.execute("""
        SELECT ca.match_id, ca.title, ca.date, ca.venue, ca.format,
               t1.name as team1_name, t2.name as team2_name
        FROM CAMatches ca
        LEFT JOIN CATeams t1 ON ca.team1_id = t1.team_id
        LEFT JOIN CATeams t2 ON ca.team2_id = t2.team_id
    """).fetchall()

    ca_count = 0
    for row in ca_rows:
        mid, title, date_str, venue, fmt, team1, team2 = row

        # If team names are NULL, try parsing from title ("Team1 v Team2 in YYYY")
        if not team1 or not team2:
            title_match = re.match(r'^(.+?)\s+v\s+(.+?)\s+in\s+', title or "")
            if title_match:
                team1 = team1 or title_match.group(1).strip()
                team2 = team2 or title_match.group(2).strip()
            else:
                team1 = team1 or "Unknown"
                team2 = team2 or "Unknown"

        date_norm = parse_fuzzy_date(date_str)
        fp = generate_fingerprint(team1, team2, date_norm, fmt)

        if fp not in registry:
            registry[fp] = {
                "team1": normalize_team(team1),
                "team2": normalize_team(team2),
                "match_date": date_norm,
                "venue": venue,
                "format": fmt,
                "ca_match_id": str(mid),
                "cricsheet_id": None,
                "cricbuzz_id": None,
                "espn_id": None,
                "scraped_id": None,
                "has_scorecard": 1,
                "has_ball_by_ball": 0,
                "has_commentary": 0,
                "source_priority": "CricketArchive",
            }
        else:
            registry[fp]["ca_match_id"] = str(mid)
            registry[fp]["has_scorecard"] = 1

        ca_count += 1

    logging.info(f"  CricketArchive: {ca_count} matches processed")

    # ============================================================
    # SOURCE 2: Cricsheet (Matches table)
    # ============================================================
    logging.info("Processing Cricsheet matches...")
    cs_rows = src.execute("""
        SELECT match_id, date, venue, format, team1_id, team2_id
        FROM Matches
    """).fetchall()

    cs_count = 0
    cs_merged = 0
    for row in cs_rows:
        mid, date_str, venue, fmt, team1, team2 = row
        date_norm = parse_fuzzy_date(date_str)
        fp = generate_fingerprint(team1, team2, date_norm, fmt)

        if fp in registry:
            # This match already exists from CricketArchive — MERGE
            registry[fp]["cricsheet_id"] = str(mid)
            registry[fp]["has_ball_by_ball"] = 1
            cs_merged += 1
        else:
            registry[fp] = {
                "team1": normalize_team(team1),
                "team2": normalize_team(team2),
                "match_date": date_norm,
                "venue": venue,
                "format": fmt,
                "ca_match_id": None,
                "cricsheet_id": str(mid),
                "cricbuzz_id": None,
                "espn_id": None,
                "scraped_id": None,
                "has_scorecard": 0,
                "has_ball_by_ball": 1,
                "has_commentary": 0,
                "source_priority": "Cricsheet",
            }

        cs_count += 1

    logging.info(f"  Cricsheet: {cs_count} matches processed, {cs_merged} merged with CricketArchive")

    # ============================================================
    # SOURCE 3: Existing MatchRegistry (Cricbuzz links)
    # ============================================================
    logging.info("Processing MatchRegistry (Cricbuzz/ESPN links)...")
    try:
        mr_rows = src.execute("""
            SELECT universal_match_id, team1, team2, match_date, format,
                   ca_id, cricbuzz_id, espn_id
            FROM MatchRegistry
        """).fetchall()

        mr_linked = 0
        for row in mr_rows:
            uid, team1, team2, date_str, fmt, ca_id, cb_id, espn_id = row
            date_norm = parse_fuzzy_date(date_str)
            fp = generate_fingerprint(team1, team2, date_norm, fmt)

            if fp in registry:
                if cb_id:
                    registry[fp]["cricbuzz_id"] = str(cb_id)
                    mr_linked += 1
                if espn_id:
                    registry[fp]["espn_id"] = str(espn_id)
            # Don't create new entries from MatchRegistry — it's just a link table

        logging.info(f"  MatchRegistry: {mr_linked} Cricbuzz IDs linked")
    except Exception as e:
        logging.warning(f"  MatchRegistry: skipped ({e})")

    # ============================================================
    # SOURCE 4: Scraped RawHTML
    # ============================================================
    logging.info("Processing ScrapedMatches...")
    try:
        sc_rows = tgt.execute("SELECT match_id, title FROM ScrapedMatches").fetchall()
        sc_linked = 0
        for row in sc_rows:
            mid, title = row
            # Link by scraped match_id if it matches a CA match_id
            for fp, data in registry.items():
                if data["ca_match_id"] == str(mid):
                    data["scraped_id"] = mid
                    sc_linked += 1
                    break
        logging.info(f"  ScrapedMatches: {sc_linked} linked")
    except Exception:
        logging.info("  ScrapedMatches: table not found, skipping")

    # ============================================================
    # WRITE TO UNIFIED REGISTRY
    # ============================================================
    logging.info(f"Writing {len(registry)} unified records...")

    for fp, data in registry.items():
        tgt.execute("""
            INSERT OR REPLACE INTO UnifiedMatchRegistry
            (universal_id, team1, team2, match_date, venue, format,
             ca_match_id, cricsheet_id, cricbuzz_id, espn_id, scraped_id,
             has_scorecard, has_ball_by_ball, has_commentary, source_priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fp,
            data["team1"], data["team2"], data["match_date"],
            data["venue"], data["format"],
            data["ca_match_id"], data["cricsheet_id"],
            data["cricbuzz_id"], data["espn_id"], data["scraped_id"],
            data["has_scorecard"], data["has_ball_by_ball"],
            data["has_commentary"], data["source_priority"],
        ))

    tgt.commit()
    src.close()
    tgt.close()

    # ============================================================
    # SUMMARY REPORT
    # ============================================================
    tgt = sqlite3.connect(TARGET_DB)
    total = tgt.execute("SELECT COUNT(*) FROM UnifiedMatchRegistry").fetchone()[0]
    with_ca = tgt.execute("SELECT COUNT(*) FROM UnifiedMatchRegistry WHERE ca_match_id IS NOT NULL").fetchone()[0]
    with_cs = tgt.execute("SELECT COUNT(*) FROM UnifiedMatchRegistry WHERE cricsheet_id IS NOT NULL").fetchone()[0]
    with_cb = tgt.execute("SELECT COUNT(*) FROM UnifiedMatchRegistry WHERE cricbuzz_id IS NOT NULL").fetchone()[0]
    with_both = tgt.execute("SELECT COUNT(*) FROM UnifiedMatchRegistry WHERE ca_match_id IS NOT NULL AND cricsheet_id IS NOT NULL").fetchone()[0]
    with_scorecard = tgt.execute("SELECT COUNT(*) FROM UnifiedMatchRegistry WHERE has_scorecard = 1").fetchone()[0]
    with_bbb = tgt.execute("SELECT COUNT(*) FROM UnifiedMatchRegistry WHERE has_ball_by_ball = 1").fetchone()[0]
    tgt.close()

    print("\n" + "=" * 60)
    print("UNIFICATION COMPLETE")
    print("=" * 60)
    print(f"Total unique matches:              {total:,}")
    print(f"With CricketArchive scorecard:     {with_ca:,}")
    print(f"With Cricsheet ball-by-ball:        {with_cs:,}")
    print(f"With Cricbuzz link:                 {with_cb:,}")
    print(f"Deduplicated (in both CA + CS):     {with_both:,}")
    print(f"Has scorecard data:                 {with_scorecard:,}")
    print(f"Has ball-by-ball data:              {with_bbb:,}")
    print("=" * 60)


if __name__ == "__main__":
    unify()
