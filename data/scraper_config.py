"""
Configuration for ESPN Cricinfo Statsguru scraper.
Comprehensive mappings for ALL international cricket teams and players.
"""

import random

# ===========================
# TEAM NAME / CODE MAPPINGS
# ===========================
# Maps country names (as shown in Statsguru results) to standard codes.
# This is comprehensive - covers all ICC full members, associates, affiliates,
# and historical teams that have ever appeared in international cricket.

TEAM_NAME_TO_CODE = {
    # ICC Full Members (12)
    "India": "IND", "Australia": "AUS", "England": "ENG",
    "Pakistan": "PAK", "South Africa": "SA", "New Zealand": "NZ",
    "Sri Lanka": "SL", "West Indies": "WI", "Bangladesh": "BAN",
    "Afghanistan": "AFG", "Ireland": "IRE", "Zimbabwe": "ZIM",
    # Associate / Affiliate Members
    "Netherlands": "NED", "Scotland": "SCO", "Kenya": "KEN",
    "Canada": "CAN", "United Arab Emirates": "UAE", "U.A.E.": "UAE",
    "Oman": "OMA", "Nepal": "NEP", "Namibia": "NAM",
    "United States of America": "USA", "U.S.A.": "USA",
    "Papua New Guinea": "PNG", "P.N.G.": "PNG",
    "Hong Kong": "HK", "Bermuda": "BER", "Uganda": "UGA",
    "Jersey": "JER", "Guernsey": "GUE", "Germany": "GER",
    "Italy": "ITA", "Denmark": "DEN", "Singapore": "SIN",
    "Malaysia": "MAL", "Thailand": "THA", "Myanmar": "MYA",
    "Tanzania": "TAN", "Vanuatu": "VAN", "Fiji": "FIJ",
    "Cayman Islands": "CAY", "Kuwait": "KUW", "Saudi Arabia": "SAU",
    "Qatar": "QAT", "Bahrain": "BHR", "Botswana": "BOT",
    "Malawi": "MAW", "Mozambique": "MOZ", "Nigeria": "NGA",
    "Ghana": "GHA", "Cameroon": "CMR", "Sierra Leone": "SLE",
    "Rwanda": "RWA", "Lesotho": "LES", "Swaziland": "SWZ",
    "Eswatini": "SWZ", "Zambia": "ZAM",
    "Argentina": "ARG", "Brazil": "BRA", "Chile": "CHL",
    "Mexico": "MEX", "Panama": "PAN", "Belize": "BLZ",
    "Costa Rica": "CRC", "Suriname": "SUR",
    "Austria": "AUT", "Belgium": "BEL", "Croatia": "CRO",
    "Czech Republic": "CZE", "Czechia": "CZE",
    "Estonia": "EST", "Finland": "FIN", "France": "FRA",
    "Gibraltar": "GIB", "Greece": "GRE", "Hungary": "HUN",
    "Isle of Man": "IOM", "Israel": "ISR", "Luxembourg": "LUX",
    "Malta": "MLT", "Norway": "NOR", "Portugal": "POR",
    "Romania": "ROM", "Russia": "RUS", "Serbia": "SRB",
    "Slovenia": "SVN", "Spain": "ESP", "Sweden": "SWE",
    "Switzerland": "SUI", "Turkey": "TUR",
    "Iran": "IRN", "Iraq": "IRQ", "Japan": "JPN",
    "South Korea": "KOR", "China": "CHN", "Taiwan": "TPE",
    "Philippines": "PHI", "Indonesia": "INA",
    "Maldives": "MDV", "Bhutan": "BHU",
    "Samoa": "SAM", "Tonga": "TGA", "Cook Islands": "COK",
    # Caribbean territories (often play separately)
    "Trinidad & Tobago": "TT", "Trinidad and Tobago": "TT",
    "Jamaica": "JAM", "Barbados": "BAR", "Guyana": "GUY",
    "Leeward Islands": "LEE", "Windward Islands": "WIN",
    "Bahamas": "BAH", "St Lucia": "STL", "St Vincent": "STV",
    "Antigua and Barbuda": "ANT", "Turks and Caicos": "TCI",
    # Historical / Special teams
    "ICC World XI": "WXI", "World XI": "WXI",
    "Asia XI": "AXI", "Africa XI": "AFX",
    "East Africa": "EAF", "ICC World XI": "WXI",
    "Marylebone Cricket Club": "MCC",
    # Short code identity mappings (when Statsguru shows codes directly)
    "IND": "IND", "AUS": "AUS", "ENG": "ENG", "PAK": "PAK",
    "SA": "SA", "NZ": "NZ", "SL": "SL", "WI": "WI",
    "BAN": "BAN", "AFG": "AFG", "IRE": "IRE", "ZIM": "ZIM",
    "NED": "NED", "SCO": "SCO", "KEN": "KEN", "CAN": "CAN",
    "UAE": "UAE", "OMA": "OMA", "NEP": "NEP", "NAM": "NAM",
    "USA": "USA", "PNG": "PNG", "HK": "HK", "BER": "BER",
    "UGA": "UGA", "JER": "JER", "GER": "GER", "ITA": "ITA",
}

# Reverse mapping: code -> full name
TEAM_CODE_TO_NAME = {}
_seen_codes = set()
for _name, _code in TEAM_NAME_TO_CODE.items():
    if _code not in _seen_codes and len(_name) > 3:
        TEAM_CODE_TO_NAME[_code] = _name
        _seen_codes.add(_code)

# ===========================
# HOME ADVANTAGE VALUES
# ===========================
HOME_ADVANTAGE = {
    "IND": 0.12, "AUS": 0.10, "ENG": 0.09, "PAK": 0.08,
    "SA": 0.09, "NZ": 0.08, "SL": 0.10, "WI": 0.07,
    "BAN": 0.09, "AFG": 0.06, "IRE": 0.06, "ZIM": 0.06,
    "NED": 0.04, "SCO": 0.04, "USA": 0.04, "NAM": 0.04,
    "OMA": 0.04, "NEP": 0.04, "PNG": 0.03, "KEN": 0.04,
    "CAN": 0.03, "UAE": 0.04, "HK": 0.03, "BER": 0.03,
}
DEFAULT_HOME_ADVANTAGE = 0.03

# ===========================
# STATSGURU URL BUILDING
# ===========================
STATSGURU_BASE = "https://stats.espncricinfo.com/ci/engine/stats/index.html"

FORMAT_CLASSES = {
    "Test": 1,
    "ODI": 2,
    "T20": 3,
}

# ===========================
# BROWSER HEADERS
# ===========================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]


def get_headers(referer=None):
    """Get browser-like request headers with a random User-Agent."""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }
    if referer:
        headers["Referer"] = referer
    return headers


# ===========================
# ROLE CLASSIFICATION
# ===========================

def classify_player_role(batting_avg, bowling_avg, batting_innings, bowling_innings):
    """
    Classify player role based on statistics.
    Returns: 'Batsman', 'Bowler', or 'Allrounder'
    (Wicketkeeper is assigned separately via KNOWN_WICKETKEEPERS)
    """
    has_bat = batting_innings >= 3 and batting_avg > 0
    has_bowl = bowling_innings >= 3 and bowling_avg > 0 and bowling_avg < 90

    if has_bat and has_bowl:
        if batting_avg >= 25 and bowling_avg <= 38:
            return "Allrounder"
        elif batting_avg >= 28:
            return "Batsman"
        elif bowling_avg <= 40:
            return "Bowler"
        else:
            return "Allrounder"
    elif has_bowl:
        return "Bowler"
    else:
        return "Batsman"


# Known wicketkeepers (team_code -> list of player names)
KNOWN_WICKETKEEPERS = {
    "IND": ["KL Rahul", "Rishabh Pant", "Sanju Samson", "Ishan Kishan",
            "Dhruv Jurel", "MS Dhoni", "Wriddhiman Saha", "Dinesh Karthik"],
    "AUS": ["Alex Carey", "Josh Inglis", "Josh Philippe", "Tim Paine",
            "Matthew Wade", "Brad Haddin", "Adam Gilchrist"],
    "ENG": ["Jos Buttler", "Jonny Bairstow", "Ben Foakes", "Jamie Smith",
            "Phil Salt", "Sam Billings", "Matt Prior"],
    "PAK": ["Mohammad Rizwan", "Sarfaraz Ahmed", "Kamran Akmal",
            "Azam Khan"],
    "SA": ["Quinton de Kock", "Heinrich Klaasen", "Kyle Verreynne",
           "AB de Villiers", "Mark Boucher"],
    "NZ": ["Tom Latham", "Tom Blundell", "Devon Conway", "BJ Watling",
           "Luke Ronchi", "Brendon McCullum"],
    "SL": ["Kusal Mendis", "Niroshan Dickwella", "Kusal Perera",
           "Dinesh Chandimal", "Kumar Sangakkara"],
    "WI": ["Shai Hope", "Joshua Da Silva", "Nicholas Pooran",
           "Denesh Ramdin", "Shane Dowrich"],
    "BAN": ["Mushfiqur Rahim", "Litton Das", "Nurul Hasan"],
    "AFG": ["Rahmanullah Gurbaz", "Ikram Alikhil", "Mohammad Shahzad"],
    "IRE": ["Lorcan Tucker", "Neil Rock", "Gary Wilson"],
    "ZIM": ["Regis Chakabva", "Clive Madande", "Brendan Taylor",
            "Tatenda Taibu"],
    "NED": ["Scott Edwards", "Wesley Barresi"],
    "SCO": ["Matthew Cross"],
    "NAM": ["Zane Green"],
    "USA": ["Monank Patel", "Andries Gous"],
    "OMA": ["Naseem Khushi", "Pratik Athavale"],
    "NEP": ["Aasif Sheikh"],
    "PNG": ["Kiplin Doriga", "Hiri Hiri"],
    "KEN": ["Morris Ouma", "Collins Obuya"],
    "CAN": ["Hamza Tariq"],
    "HK": ["Aizaz Khan"],
}

# Known captains (team_code -> list of captain names, current first)
KNOWN_CAPTAINS = {
    "IND": ["Rohit Sharma", "Suryakumar Yadav", "Jasprit Bumrah"],
    "AUS": ["Pat Cummins", "Mitchell Marsh", "Steve Smith"],
    "ENG": ["Ben Stokes", "Jos Buttler", "Joe Root"],
    "PAK": ["Shan Masood", "Babar Azam", "Mohammad Rizwan"],
    "SA": ["Temba Bavuma", "Aiden Markram"],
    "NZ": ["Tom Latham", "Mitchell Santner", "Kane Williamson"],
    "SL": ["Dhananjaya de Silva", "Charith Asalanka"],
    "WI": ["Kraigg Brathwaite", "Rovman Powell", "Shai Hope"],
    "BAN": ["Najmul Hossain Shanto"],
    "AFG": ["Hashmatullah Shahidi", "Rashid Khan", "Ibrahim Zadran"],
    "IRE": ["Andrew Balbirnie", "Paul Stirling"],
    "ZIM": ["Craig Ervine", "Sikandar Raza"],
    "NED": ["Scott Edwards"],
    "SCO": ["Richie Berrington"],
    "NAM": ["Gerhard Erasmus"],
    "USA": ["Monank Patel"],
    "OMA": ["Aqib Ilyas"],
    "NEP": ["Rohit Paudel"],
}

# ===========================
# RATE LIMITING
# ===========================
MIN_REQUEST_DELAY = 2.5   # Min seconds between requests
MAX_REQUEST_DELAY = 4.5   # Max seconds between requests
MAX_RETRIES = 3           # Max retry attempts
RETRY_BACKOFF = 6.0       # Base backoff seconds

# ===========================
# CACHE DURATIONS (seconds)
# ===========================
CACHE_DURATION_TEAMS = 86400  # 24 hours
