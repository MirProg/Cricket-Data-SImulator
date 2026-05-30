"""
Live Match Tracker & Commentary
================================
Fetches live cricket match data and ball-by-ball commentary from ESPN Cricinfo.

Uses multiple approaches in fallback order:
  1. ESPN general sports API (site.api.espn.com)
  2. ESPN Cricinfo main site (__NEXT_DATA__ extraction)
  3. hs-consumer-api (last resort)

Live commentary is polled periodically for real-time updates.
"""

import json
import requests
import time
import random
import re
import sys
from typing import Dict, List, Optional

# Ensure stdout can handle emojis on Windows
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
from . import scraper_config as cfg
import logging

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


class LiveTracker:
    """
    Track live cricket matches and retrieve ball-by-ball commentary.
    """

    # ESPN general sports API (more accessible than hs-consumer-api)
    ESPN_API_BASE = "https://site.api.espn.com/apis/site/v2/sports/cricket"
    # Known league slugs for ESPN API
    LEAGUES = {
        "icc": "11340",     # ICC events
        "ipl": "8048",      # IPL
        "bbl": "8044",      # Big Bash
        "cpl": "11287",     # CPL
        "psl": "11293",     # PSL
        "sa20": "17027",    # SA20
    }

    # hs-consumer-api (fallback — may be blocked)
    HS_API_BASE = "https://hs-consumer-api.espncricinfo.com/v1/pages"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(cfg.get_headers(
            referer="https://www.espncricinfo.com/live-cricket-score"
        ))

    # ================================================================
    #  ESPN GENERAL API (Primary for live data)
    # ================================================================

    def _espn_api_get(self, endpoint: str) -> Optional[Dict]:
        """Fetch from ESPN general sports API."""
        url = f"{self.ESPN_API_BASE}/{endpoint}"
        try:
            self.session.headers["User-Agent"] = random.choice(cfg.USER_AGENTS)
            resp = self.session.get(url, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            logger.debug(f"ESPN API {resp.status_code}: {url}")
            return None
        except Exception as e:
            logger.debug(f"ESPN API error: {e}")
            return None

    def get_live_matches(self) -> List[Dict]:
        """
        Get all currently live cricket matches.
        Returns list of match dicts with basic info.
        """
        matches = []

        # Try ESPN general API scoreboard
        data = self._espn_api_get("scoreboard")
        if data and "events" in data:
            for event in data["events"]:
                match = self._parse_espn_event(event)
                if match:
                    matches.append(match)
            if matches:
                return matches

        # Try specific league scoreboards
        for league_name, league_id in self.LEAGUES.items():
            data = self._espn_api_get(f"{league_id}/scoreboard")
            if data and "events" in data:
                for event in data["events"]:
                    match = self._parse_espn_event(event)
                    if match:
                        matches.append(match)

        # Fallback: try main ESPNCricinfo site
        if not matches:
            matches = self._scrape_live_page()

        # Fallback: try hs-consumer-api
        if not matches:
            matches = self._try_hs_api_live()

        return matches

    def _parse_espn_event(self, event: Dict) -> Optional[Dict]:
        """Parse an ESPN API event object into a match dict."""
        try:
            competitions = event.get("competitions", [])
            if not competitions:
                return None
            comp = competitions[0]

            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                return None

            team1 = competitors[0]
            team2 = competitors[1]

            status = comp.get("status", {})
            status_type = status.get("type", {})
            state = status_type.get("state", "")
            detail = status_type.get("detail", "")
            description = status_type.get("description", "")

            match = {
                "match_id": str(event.get("id", "")),
                "name": event.get("name", ""),
                "short_name": event.get("shortName", ""),
                "status": state,  # "pre", "in", "post"
                "status_detail": detail or description,
                "team1": {
                    "name": team1.get("team", {}).get("displayName", ""),
                    "abbreviation": team1.get("team", {}).get("abbreviation", ""),
                    "score": team1.get("score", ""),
                },
                "team2": {
                    "name": team2.get("team", {}).get("displayName", ""),
                    "abbreviation": team2.get("team", {}).get("abbreviation", ""),
                    "score": team2.get("score", ""),
                },
                "venue": comp.get("venue", {}).get("fullName", ""),
                "series": event.get("season", {}).get("name", ""),
                "start_time": event.get("date", ""),
                "format": self._detect_format(event.get("name", "")),
            }

            # Extract innings details if available
            innings = []
            for competitor in competitors:
                linescores = competitor.get("linescores", [])
                for i, ls in enumerate(linescores):
                    innings.append({
                        "team": competitor.get("team", {}).get("abbreviation", ""),
                        "innings_num": i + 1,
                        "runs": ls.get("runs", 0),
                        "wickets": ls.get("wickets", 0),
                        "overs": ls.get("overs", 0),
                    })
            match["innings"] = innings

            # Extract current batting/bowling
            situation = comp.get("situation", {})
            if situation:
                match["situation"] = {
                    "current_batsman": situation.get("lastBattingTeam", {}).get("displayName", ""),
                    "current_over": situation.get("over", ""),
                    "current_rr": situation.get("currentRunRate", ""),
                    "required_rr": situation.get("requiredRunRate", ""),
                    "last_wicket": situation.get("lastWicket", ""),
                    "note": situation.get("note", ""),
                }

            return match
        except Exception as e:
            logger.debug(f"  Event parse error: {e}")
            return None

    def _detect_format(self, name: str) -> str:
        """Detect match format from event name."""
        name_lower = name.lower()
        if "test" in name_lower:
            return "Test"
        elif "t20" in name_lower or "twenty20" in name_lower:
            return "T20"
        elif "odi" in name_lower or "one day" in name_lower:
            return "ODI"
        elif "ipl" in name_lower or "bbl" in name_lower or "cpl" in name_lower:
            return "T20"
        return "Unknown"

    # ================================================================
    #  LIVE SCORES PAGE SCRAPING (Fallback)
    # ================================================================

    def _scrape_live_page(self) -> List[Dict]:
        """Try scraping the ESPN Cricinfo live scores page."""
        url = "https://www.espncricinfo.com/live-cricket-score"
        try:
            self.session.headers["User-Agent"] = random.choice(cfg.USER_AGENTS)
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return []

            if not HAS_BS4:
                return []

            soup = BeautifulSoup(resp.text, "lxml")

            # Try __NEXT_DATA__
            script = soup.find("script", id="__NEXT_DATA__")
            if script and script.string:
                try:
                    data = json.loads(script.string)
                    return self._parse_next_data_live(data)
                except json.JSONDecodeError:
                    pass

            return []
        except Exception as e:
            logger.debug(f"  Live page scrape error: {e}")
            return []

    def _parse_next_data_live(self, data: Dict) -> List[Dict]:
        """Extract live match data from __NEXT_DATA__ JSON."""
        matches = []
        try:
            # Navigate through Next.js data structure
            page_props = data.get("props", {}).get("pageProps", {})
            # The exact structure varies; try common paths
            for key in ["data", "appData", "content"]:
                content = page_props.get(key, {})
                if isinstance(content, dict):
                    for sub_key in ["matches", "events", "liveMatches"]:
                        match_list = content.get(sub_key, [])
                        if isinstance(match_list, list):
                            for m in match_list:
                                parsed = self._parse_next_data_match(m)
                                if parsed:
                                    matches.append(parsed)
        except Exception as e:
            logger.debug(f"  __NEXT_DATA__ parse error: {e}")
        return matches

    def _parse_next_data_match(self, m: Dict) -> Optional[Dict]:
        """Parse a single match from __NEXT_DATA__."""
        try:
            return {
                "match_id": str(m.get("objectId", m.get("id", ""))),
                "name": m.get("title", m.get("name", "")),
                "status": m.get("state", m.get("status", "")),
                "status_detail": m.get("statusText", m.get("statusDetail", "")),
                "team1": {"name": m.get("team1", {}).get("name", ""), "score": ""},
                "team2": {"name": m.get("team2", {}).get("name", ""), "score": ""},
                "venue": m.get("ground", {}).get("name", ""),
                "format": m.get("format", ""),
            }
        except Exception:
            return None

    # ================================================================
    #  HS-CONSUMER-API (Last Resort)
    # ================================================================

    def _try_hs_api_live(self) -> List[Dict]:
        """Try the hs-consumer-api for live match data. Often blocked."""
        urls = [
            f"{self.HS_API_BASE}/matches/live",
            f"{self.HS_API_BASE}/matches/current",
        ]
        for url in urls:
            try:
                self.session.headers["User-Agent"] = random.choice(cfg.USER_AGENTS)
                resp = self.session.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    # Parse HS API response
                    if isinstance(data, list):
                        return [{"match_id": str(m.get("id", "")),
                                 "name": m.get("title", ""),
                                 "status": m.get("state", "")}
                                for m in data]
            except Exception:
                continue
        return []

    # ================================================================
    #  MATCH DETAILS
    # ================================================================

    def get_match_details(self, match_id: str) -> Optional[Dict]:
        """Get detailed information for a specific match."""
        # Try ESPN API
        data = self._espn_api_get(f"summary?event={match_id}")
        if data:
            return self._parse_match_summary(data)

        # Try hs-consumer-api
        url = f"{self.HS_API_BASE}/match/home?matchId={match_id}"
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass

        return None

    def _parse_match_summary(self, data: Dict) -> Dict:
        """Parse ESPN API match summary."""
        summary = {
            "header": {},
            "scorecards": [],
            "batting": [],
            "bowling": [],
        }

        # Header
        header = data.get("header", {})
        if header:
            competitions = header.get("competitions", [])
            if competitions:
                comp = competitions[0]
                summary["header"] = {
                    "status": comp.get("status", {}).get("type", {}).get("detail", ""),
                    "venue": comp.get("venue", {}).get("fullName", ""),
                }

        # Rosters / Scorecards
        rosters = data.get("rosters", [])
        for roster in rosters:
            team_name = roster.get("team", {}).get("displayName", "")
            for player in roster.get("roster", []):
                p = {
                    "name": player.get("athlete", {}).get("displayName", ""),
                    "team": team_name,
                }
                # Check for batting/bowling stats
                for stat in player.get("statistics", []):
                    if stat.get("type") == "batting":
                        p["batting"] = {s["name"]: s["displayValue"]
                                        for s in stat.get("stats", [])}
                    elif stat.get("type") == "bowling":
                        p["bowling"] = {s["name"]: s["displayValue"]
                                        for s in stat.get("stats", [])}
                summary["scorecards"].append(p)

        return summary

    # ================================================================
    #  COMMENTARY
    # ================================================================

    def get_commentary(self, match_id: str, innings: int = 1,
                       page: int = 1) -> List[Dict]:
        """
        Get ball-by-ball commentary for a match.

        Args:
            match_id: ESPN match ID
            innings: Innings number (1, 2, 3, 4)
            page: Page of commentary (newer first)

        Returns:
            List of commentary dicts, newest first
        """
        commentaries = []

        # Try ESPN API play-by-play
        data = self._espn_api_get(f"playbyplay?event={match_id}")
        if data:
            items = data.get("commentary", data.get("items", []))
            if isinstance(items, list):
                for item in items:
                    comm = self._parse_commentary_item(item)
                    if comm:
                        commentaries.append(comm)
                if commentaries:
                    return commentaries

        # Try hs-consumer-api commentary endpoint
        url = (f"{self.HS_API_BASE}/match/commentary"
               f"?matchId={match_id}&inningNumber={innings}&page={page}")
        try:
            self.session.headers["User-Agent"] = random.choice(cfg.USER_AGENTS)
            resp = self.session.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("commentaryList", data.get("comments", []))
                if isinstance(items, list):
                    for item in items:
                        comm = self._parse_hs_commentary(item)
                        if comm:
                            commentaries.append(comm)
        except Exception as e:
            logger.debug(f"  HS commentary error: {e}")

        # Fallback: scrape match page
        if not commentaries:
            commentaries = self._scrape_commentary_page(match_id)

        return commentaries

    def _parse_commentary_item(self, item: Dict) -> Optional[Dict]:
        """Parse an ESPN API commentary item."""
        try:
            return {
                "over": item.get("over", {}).get("number", ""),
                "ball": item.get("over", {}).get("ball", ""),
                "runs": item.get("scoreValue", 0),
                "batsman": item.get("batsman", {}).get("athlete", {}).get("displayName", ""),
                "bowler": item.get("bowler", {}).get("athlete", {}).get("displayName", ""),
                "text": item.get("text", item.get("shortText", "")),
                "is_wicket": item.get("dismissal", {}).get("text", "") != "",
                "is_boundary": item.get("isBoundary", False) or item.get("isSix", False),
                "dismissal": item.get("dismissal", {}).get("text", ""),
                "type": self._classify_ball(item),
            }
        except Exception:
            return None

    def _parse_hs_commentary(self, item: Dict) -> Optional[Dict]:
        """Parse an hs-consumer-api commentary item."""
        try:
            return {
                "over": item.get("overNumber", ""),
                "ball": item.get("ballNumber", ""),
                "runs": item.get("totalRuns", 0),
                "batsman": item.get("batsmanStriker", {}).get("name", ""),
                "bowler": item.get("bowlerStriker", {}).get("name", ""),
                "text": item.get("commentTextItems", [{}])[0].get("html", "")
                        if item.get("commentTextItems") else item.get("text", ""),
                "is_wicket": bool(item.get("isWicket", False)),
                "is_boundary": bool(item.get("isBoundary", False)),
                "dismissal": item.get("dismissalText", ""),
                "type": "wicket" if item.get("isWicket") else
                        "boundary" if item.get("isBoundary") else "ball",
            }
        except Exception:
            return None

    def _classify_ball(self, item: Dict) -> str:
        """Classify ball type from commentary item."""
        if item.get("dismissal", {}).get("text"):
            return "wicket"
        if item.get("isSix", False):
            return "six"
        if item.get("isBoundary", False):
            return "four"
        score = item.get("scoreValue", 0)
        if score == 0:
            return "dot"
        return "runs"

    def _scrape_commentary_page(self, match_id: str) -> List[Dict]:
        """Fallback: scrape commentary from match web page."""
        urls = [
            f"https://www.espncricinfo.com/matches/engine/match/{match_id}.html",
            f"https://www.espncricinfo.com/series/_/gameId/{match_id}",
        ]
        for url in urls:
            try:
                self.session.headers["User-Agent"] = random.choice(cfg.USER_AGENTS)
                resp = self.session.get(url, timeout=15)
                if resp.status_code != 200:
                    continue

                if not HAS_BS4:
                    continue

                soup = BeautifulSoup(resp.text, "lxml")
                script = soup.find("script", id="__NEXT_DATA__")
                if script and script.string:
                    data = json.loads(script.string)
                    return self._extract_commentary_from_next_data(data)
            except Exception:
                continue
        return []

    def _extract_commentary_from_next_data(self, data: Dict) -> List[Dict]:
        """Extract commentary from __NEXT_DATA__ JSON."""
        commentaries = []
        try:
            pp = data.get("props", {}).get("pageProps", {})
            for path_key in ["data", "appData"]:
                content = pp.get(path_key, {})
                if isinstance(content, dict):
                    for ck in ["commentary", "commentaryList", "recentBalls"]:
                        items = content.get(ck, [])
                        if isinstance(items, list):
                            for item in items:
                                text = item.get("text", item.get("html", ""))
                                if text:
                                    commentaries.append({
                                        "over": item.get("over", ""),
                                        "text": re.sub(r'<[^>]+>', '', str(text)),
                                        "runs": item.get("runs", 0),
                                        "is_wicket": bool(item.get("isWicket")),
                                        "type": "wicket" if item.get("isWicket") else "ball",
                                    })
        except Exception as e:
            logger.debug(f"  __NEXT_DATA__ commentary extract error: {e}")
        return commentaries

    # ================================================================
    #  LIVE FEED (Polling)
    # ================================================================

    def start_live_feed(self, match_id: str, interval: int = 30):
        """
        Start a live commentary feed that polls for updates.
        Prints new commentary balls as they come in.

        Args:
            match_id: ESPN match ID
            interval: Polling interval in seconds
        """
        print(f"\n🔴 LIVE FEED — Match {match_id}")
        print(f"   Polling every {interval}s. Press Ctrl+C to stop.\n")
        print("─" * 60)

        seen_texts = set()

        try:
            while True:
                # Get match status
                matches = self.get_live_matches()
                current = None
                for m in matches:
                    if str(m.get("match_id", "")) == str(match_id):
                        current = m
                        break

                if current:
                    t1 = current.get("team1", {})
                    t2 = current.get("team2", {})
                    status = current.get("status_detail", "")
                    print(f"\r  📊 {t1.get('name', '?')} {t1.get('score', '')} vs "
                          f"{t2.get('name', '?')} {t2.get('score', '')}  |  {status}")

                # Get commentary
                commentary = self.get_commentary(match_id)
                new_items = []
                for c in commentary:
                    text = c.get("text", "")
                    if text and text not in seen_texts:
                        seen_texts.add(text)
                        new_items.append(c)

                # Print new commentary (newest last)
                for c in reversed(new_items):
                    over = c.get("over", "")
                    text = c.get("text", "")
                    ball_type = c.get("type", "")

                    # Colorize based on type
                    prefix = "  "
                    if ball_type == "wicket":
                        prefix = "  🔴 W  "
                    elif ball_type == "six":
                        prefix = "  🟢 6  "
                    elif ball_type == "four":
                        prefix = "  🟡 4  "
                    elif ball_type == "dot":
                        prefix = "  ⚪ .  "
                    else:
                        runs = c.get("runs", 0)
                        prefix = f"  ⚾ {runs}  "

                    over_str = f"[{over}] " if over else ""
                    print(f"{prefix}{over_str}{text}")

                # Check if match ended
                if current and current.get("status", "") == "post":
                    print("\n  🏁 Match has concluded.")
                    break

                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n  ⏹ Live feed stopped.")


# ================================================================
#  DISPLAY HELPERS
# ================================================================

def display_live_matches(matches: List[Dict]):
    """Pretty-print a list of live matches."""
    if not matches:
        print("\n  No live matches found at the moment.")
        print("  (ESPN API may be temporarily unavailable)")
        return

    print(f"\n{'=' * 64}")
    print(f"  🏏 LIVE CRICKET MATCHES ({len(matches)} found)")
    print(f"{'=' * 64}")

    for i, m in enumerate(matches, 1):
        t1 = m.get("team1", {})
        t2 = m.get("team2", {})
        status = m.get("status", "")
        detail = m.get("status_detail", "")
        venue = m.get("venue", "")
        fmt = m.get("format", "")
        mid = m.get("match_id", "")

        status_emoji = {"pre": "⏳", "in": "🔴", "post": "✅"}.get(status, "❓")

        print(f"\n  {status_emoji} Match #{mid}")
        print(f"    {t1.get('name', '?')} {t1.get('score', '')}  vs  "
              f"{t2.get('name', '?')} {t2.get('score', '')}")
        if detail:
            print(f"    Status: {detail}")
        if venue:
            print(f"    Venue: {venue}")
        if fmt:
            print(f"    Format: {fmt}")

        # Show innings if available
        innings = m.get("innings", [])
        if innings:
            for inn in innings:
                print(f"    📋 Inns {inn.get('innings_num', '?')}: "
                      f"{inn.get('team', '?')} "
                      f"{inn.get('runs', 0)}/{inn.get('wickets', 0)} "
                      f"({inn.get('overs', 0)} ov)")

    print(f"\n{'=' * 64}")
    print("  Use 'commentary <match_id>' to see ball-by-ball commentary")
    print("  Use 'livefeed <match_id>' for real-time updates")
    print(f"{'=' * 64}")


def display_commentary(commentary: List[Dict], match_id: str):
    """Pretty-print match commentary."""
    if not commentary:
        print(f"\n  No commentary available for match {match_id}.")
        print("  (The match may not have started, or the API is unavailable)")
        return

    print(f"\n{'=' * 64}")
    print(f"  🎙️  BALL-BY-BALL COMMENTARY — Match {match_id}")
    print(f"{'=' * 64}\n")

    for c in commentary[:50]:  # Show latest 50 balls
        over = c.get("over", "")
        text = c.get("text", "")
        ball_type = c.get("type", "ball")

        prefix = "  "
        if ball_type == "wicket":
            prefix = "  🔴 W  "
        elif ball_type == "six":
            prefix = "  🟢 6  "
        elif ball_type == "four":
            prefix = "  🟡 4  "
        elif ball_type == "dot":
            prefix = "  ⚪ .  "
        else:
            runs = c.get("runs", 0)
            prefix = f"  ⚾ {runs}  "

        over_str = f"[{over}] " if over else ""
        # Truncate long text
        if len(text) > 100:
            text = text[:97] + "…"
        print(f"{prefix}{over_str}{text}")

    if len(commentary) > 50:
        print(f"\n  … and {len(commentary) - 50} more balls")

    print(f"\n{'=' * 64}")
