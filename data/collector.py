"""
ESPN Cricinfo Statsguru Data Collector
======================================
Scrapes ALL teams and ALL players from the complete history of international cricket.
Coverage: Test (1877+), ODI (1971+), T20I (2005+) — every player, every team, ever.

Uses Statsguru HTML table scraping with anti-detection measures:
  - Rotating browser User-Agents
  - Rate limiting with random delays
  - Session management with cookie persistence
  - Retry with exponential backoff
  - Aggressive caching (24h)

Fallback chain: Statsguru scrape → cached data → sample data
"""

import json
import requests
import time
import random
import re
import io
import sys
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

# Ensure stdout can handle emojis on Windows
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
try:
    from .models import Team, Player, MatchFormat, PlayerRole
    from . import scraper_config as cfg
except ImportError:
    from models import Team, Player, MatchFormat, PlayerRole
    import scraper_config as cfg
import logging

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    logger.warning("pandas not installed — run: pip install pandas lxml")

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


class CricketDataCollector:
    """
    Comprehensive cricket data collector.
    Scrapes ESPN Cricinfo Statsguru for ALL historical international cricket statistics.
    No date filters, no team filters — gets everything.
    """

    PAGE_SIZE = 200  # Statsguru supports up to 200 results per page

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.teams_file = self.data_dir / "teams.json"
        self.session = None
        self.request_count = 0
        self.cache_duration = cfg.CACHE_DURATION_TEAMS

    # ================================================================
    #  HTTP LAYER
    # ================================================================

    def _get_session(self) -> requests.Session:
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update(cfg.get_headers(
                referer="https://stats.espncricinfo.com/"
            ))
        return self.session

    def _reset_session(self):
        if self.session:
            try:
                self.session.close()
            except Exception:
                pass
        self.session = None

    def fetch_from_api(self, url: str, headers: Dict = None) -> Optional[Dict]:
        """Fetch JSON from an API endpoint (legacy interface)."""
        try:
            resp = requests.get(url, headers=headers or cfg.get_headers(), timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"API fetch failed for {url}: {e}")
            return None

    def _fetch(self, url: str, retry: int = 0) -> Optional[str]:
        """Fetch a URL with rate limiting and retry. Returns raw HTML or None."""
        # Rate limiting / backoff
        if retry > 0:
            backoff = cfg.RETRY_BACKOFF * (2 ** (retry - 1))
            time.sleep(backoff)
        else:
            time.sleep(random.uniform(cfg.MIN_REQUEST_DELAY, cfg.MAX_REQUEST_DELAY))

        session = self._get_session()
        session.headers["User-Agent"] = random.choice(cfg.USER_AGENTS)

        try:
            resp = session.get(url, timeout=30)
            self.request_count += 1

            if resp.status_code == 200:
                return resp.text

            logger.warning(f"  HTTP {resp.status_code} → {url[:90]}…")

            if resp.status_code in (403, 429) and retry < cfg.MAX_RETRIES:
                self._reset_session()
                return self._fetch(url, retry + 1)

            if retry < cfg.MAX_RETRIES:
                return self._fetch(url, retry + 1)
            return None

        except requests.RequestException as e:
            logger.error(f"  Request error: {e}")
            if retry < cfg.MAX_RETRIES:
                return self._fetch(url, retry + 1)
            return None

    # ================================================================
    #  STATSGURU URL BUILDING
    # ================================================================

    def _build_url(self, format_class: int, stat_type: str, page: int = 1) -> str:
        """Build Statsguru query URL — all-time, all teams, paginated."""
        params = ";".join([
            f"class={format_class}",
            "template=results",
            f"type={stat_type}",
            f"page={page}",
            f"size={self.PAGE_SIZE}",
        ])
        return f"{cfg.STATSGURU_BASE}?{params}"

    # ================================================================
    #  HTML TABLE PARSING
    # ================================================================

    def _find_data_table(self, html: str, stat_type: str) -> Optional[Any]:
        """Find the main data table from Statsguru HTML among all tables."""
        if not HAS_PANDAS:
            return None
        try:
            tables = pd.read_html(io.StringIO(html))
        except Exception as e:
            logger.debug(f"  read_html error: {e}")
            return None

        if not tables:
            return None

        markers = {
            "batting": ["mat", "inns", "runs", "ave"],
            "bowling": ["mat", "inns", "wkts", "ave"],
        }
        target = markers.get(stat_type, markers["batting"])

        best, best_score = None, 0
        for df in tables:
            if len(df) < 1 or len(df.columns) < 5:
                continue
            cols = [str(c).lower().strip() for c in df.columns]
            score = sum(1 for t in target if t in cols)
            if score > best_score:
                best_score = score
                best = df

        # Fallback: index 2 is typical Statsguru layout
        if best is None and len(tables) > 2 and len(tables[2]) > 0:
            best = tables[2]
        # Last resort: largest table
        if best is None:
            big = [t for t in tables if len(t) > 1 and len(t.columns) >= 5]
            if big:
                best = max(big, key=len)
        return best

    def _detect_total_pages(self, html: str) -> int:
        """Detect total number of result pages from Statsguru pagination."""
        # Quick regex on raw HTML (works even without BS4)
        m = re.search(r'Page\s+\d+\s+of\s+(\d+)', html)
        if m:
            return int(m.group(1))

        if HAS_BS4:
            try:
                soup = BeautifulSoup(html, "lxml")
            except Exception:
                try:
                    soup = BeautifulSoup(html, "html.parser")
                except Exception:
                    return 1
            links = soup.find_all("a", href=re.compile(r"page=\d+"))
            if links:
                pages = []
                for a in links:
                    pm = re.search(r"page=(\d+)", a.get("href", ""))
                    if pm:
                        pages.append(int(pm.group(1)))
                if pages:
                    return max(pages)
        return 1

    # ================================================================
    #  UTILITY HELPERS
    # ================================================================

    def _col(self, df, *names):
        """Find a DataFrame column by trying multiple names (case-insensitive)."""
        col_map = {str(c).lower().strip(): c for c in df.columns}
        for n in names:
            if n.lower() in col_map:
                return col_map[n.lower()]
        return None

    def _f(self, val, default=0.0) -> float:
        """Safely parse float from Statsguru cell."""
        try:
            s = str(val).replace("*", "").replace("-", "").replace("DNB", "").replace("TDNB", "").strip()
            return float(s) if s and s.lower() != "nan" else default
        except (ValueError, TypeError):
            return default

    def _i(self, val, default=0) -> int:
        """Safely parse int from Statsguru cell."""
        try:
            s = str(val).replace("*", "").replace("-", "").replace("DNB", "").strip()
            return int(float(s)) if s and s.lower() != "nan" else default
        except (ValueError, TypeError):
            return default

    def _parse_player_team(self, player_val, country_val=None) -> Tuple[str, str]:
        """Extract clean player name and team code from table cell values."""
        name = re.sub(r'[†*#\u2020\u2021]', '', str(player_val)).strip()

        # "Name (TEAM)" format
        m = re.match(r'^(.+?)\s*\(([^)]+)\)\s*$', name)
        if m:
            name, team = m.group(1).strip(), m.group(2).strip()
        elif country_val and str(country_val).strip().lower() not in ('nan', '', 'none'):
            team = str(country_val).strip()
        else:
            team = "UNK"

        # Normalize to standard code
        team = cfg.TEAM_NAME_TO_CODE.get(team,
               cfg.TEAM_NAME_TO_CODE.get(team.title(),
               cfg.TEAM_NAME_TO_CODE.get(team.upper(), team)))

        # Auto-abbreviate truly unknown long names
        if len(team) > 5:
            words = team.split()
            team = "".join(w[0].upper() for w in words[:3]) if len(words) >= 2 else team[:3].upper()

        return name, team

    # ================================================================
    #  ROW PARSERS
    # ================================================================

    def _parse_batting_rows(self, df) -> List[Dict]:
        """Parse all rows from a batting stats DataFrame."""
        records = []
        pc = self._col(df, "Player", "player") or df.columns[0]
        cc = self._col(df, "Country", "country", "Team", "team")
        sc = self._col(df, "Span", "span")
        mc = self._col(df, "Mat", "mat", "Matches")
        ic = self._col(df, "Inns", "inns")
        nc = self._col(df, "NO", "no")
        rc = self._col(df, "Runs", "runs")
        hc = self._col(df, "HS", "hs")
        ac = self._col(df, "Ave", "ave", "Avg")
        bc = self._col(df, "BF", "bf", "Balls")
        src = self._col(df, "SR", "sr")
        h100 = self._col(df, "100", "100s")
        h50  = self._col(df, "50", "50s")
        f4   = self._col(df, "4s", "fours")
        f6   = self._col(df, "6s", "sixes")

        for _, row in df.iterrows():
            try:
                pv = str(row.get(pc, ""))
                if not pv or pv.lower() in ("nan", "overall", "total", ""):
                    continue
                name, team = self._parse_player_team(pv, row.get(cc) if cc else None)
                if not name or len(name) < 2:
                    continue
                records.append({
                    "name": name, "team": team,
                    "span": str(row.get(sc, "")) if sc else "",
                    "matches":    self._i(row.get(mc, 0))  if mc else 0,
                    "innings":    self._i(row.get(ic, 0))  if ic else 0,
                    "not_outs":   self._i(row.get(nc, 0))  if nc else 0,
                    "runs":       self._i(row.get(rc, 0))  if rc else 0,
                    "highest":    str(row.get(hc, "0"))     if hc else "0",
                    "batting_avg": self._f(row.get(ac, 0)) if ac else 0.0,
                    "balls_faced": self._i(row.get(bc, 0)) if bc else 0,
                    "batting_sr":  self._f(row.get(src, 0)) if src else 0.0,
                    "hundreds":   self._i(row.get(h100, 0)) if h100 else 0,
                    "fifties":    self._i(row.get(h50, 0))  if h50 else 0,
                    "fours":      self._i(row.get(f4, 0))   if f4 else 0,
                    "sixes":      self._i(row.get(f6, 0))   if f6 else 0,
                })
            except Exception:
                continue
        return records

    def _parse_bowling_rows(self, df) -> List[Dict]:
        """Parse all rows from a bowling stats DataFrame."""
        records = []
        pc = self._col(df, "Player", "player") or df.columns[0]
        cc = self._col(df, "Country", "country", "Team", "team")
        sc = self._col(df, "Span", "span")
        mc = self._col(df, "Mat", "mat")
        ic = self._col(df, "Inns", "inns")
        oc = self._col(df, "Overs", "overs", "Balls", "balls")
        mdc = self._col(df, "Mdns", "mdns")
        rc = self._col(df, "Runs", "runs")
        wc = self._col(df, "Wkts", "wkts")
        bic = self._col(df, "BBI", "bbi")
        bmc = self._col(df, "BBM", "bbm")
        ac = self._col(df, "Ave", "ave", "Avg")
        ec = self._col(df, "Econ", "econ")
        src = self._col(df, "SR", "sr")
        f5 = self._col(df, "5", "5w", "5Wi")
        f10 = self._col(df, "10", "10w")

        for _, row in df.iterrows():
            try:
                pv = str(row.get(pc, ""))
                if not pv or pv.lower() in ("nan", "overall", "total", ""):
                    continue
                name, team = self._parse_player_team(pv, row.get(cc) if cc else None)
                if not name or len(name) < 2:
                    continue
                records.append({
                    "name": name, "team": team,
                    "span": str(row.get(sc, "")) if sc else "",
                    "matches":       self._i(row.get(mc, 0))  if mc else 0,
                    "innings":       self._i(row.get(ic, 0))  if ic else 0,
                    "overs":         self._f(row.get(oc, 0))  if oc else 0.0,
                    "maidens":       self._i(row.get(mdc, 0)) if mdc else 0,
                    "runs_conceded": self._i(row.get(rc, 0))  if rc else 0,
                    "wickets":       self._i(row.get(wc, 0))  if wc else 0,
                    "bbi":           str(row.get(bic, "0/0")) if bic else "0/0",
                    "bowling_avg":   self._f(row.get(ac, 0))  if ac else 0.0,
                    "economy":       self._f(row.get(ec, 0))  if ec else 0.0,
                    "bowling_sr":    self._f(row.get(src, 0)) if src else 0.0,
                    "five_wickets":  self._i(row.get(f5, 0))  if f5 else 0,
                    "ten_wickets":   self._i(row.get(f10, 0)) if f10 else 0,
                })
            except Exception:
                continue
        return records

    # ================================================================
    #  MULTI-PAGE SCRAPING
    # ================================================================

    def _scrape_all_pages(self, format_class: int, stat_type: str,
                          label: str, max_pages: int = None) -> List[Dict]:
        """Scrape all pages of a Statsguru query. Paginates until done."""
        all_records: List[Dict] = []
        page = 1
        total_pages = None
        empty_streak = 0
        parser = self._parse_batting_rows if stat_type == "batting" else self._parse_bowling_rows

        while True:
            if max_pages and page > max_pages:
                break

            url = self._build_url(format_class, stat_type, page)
            pg = f"{page}/{total_pages}" if total_pages else str(page)
            sys.stdout.write(f"\r  📊 {label} — page {pg} ({len(all_records)} records)   ")
            sys.stdout.flush()

            html = self._fetch(url)
            if html is None:
                empty_streak += 1
                if empty_streak >= 3:
                    break
                page += 1
                continue

            if total_pages is None:
                total_pages = self._detect_total_pages(html)

            df = self._find_data_table(html, stat_type)
            if df is None or len(df) == 0:
                empty_streak += 1
                if empty_streak >= 3:
                    break
                page += 1
                continue

            empty_streak = 0
            records = parser(df)
            all_records.extend(records)

            if total_pages and page >= total_pages:
                break
            if len(records) < self.PAGE_SIZE // 2:
                # Significantly fewer results than page size → likely last page
                break
            
            import random, time
            time.sleep(random.uniform(1.5, 3.0))
            page += 1

        print(f"\r  ✅ {label}: {len(all_records)} players across {page} pages                ")
        return all_records

    # ================================================================
    #  DATA AGGREGATION  &  TEAM BUILDING
    # ================================================================

    def _merge_and_build(self, all_batting: Dict[str, List],
                         all_bowling: Dict[str, List]) -> Dict[str, Team]:
        """
        Merge batting & bowling records across all formats.
        Build Team objects with weighted-average stats per player.
        """

        # ---- Step 1: Index by (name, team, format) ----
        players: Dict[Tuple, Dict] = {}

        for fmt, recs in all_batting.items():
            for r in recs:
                k = (r["name"], r["team"])
                if k not in players:
                    players[k] = {"name": r["name"], "team": r["team"],
                                  "formats": {}, "span": ""}
                players[k]["formats"].setdefault(fmt, {})["bat"] = r
                if r.get("span", "") > players[k]["span"]:
                    players[k]["span"] = r["span"]

        for fmt, recs in all_bowling.items():
            for r in recs:
                k = (r["name"], r["team"])
                if k not in players:
                    players[k] = {"name": r["name"], "team": r["team"],
                                  "formats": {}, "span": ""}
                players[k]["formats"].setdefault(fmt, {})["bowl"] = r
                if r.get("span", "") > players[k]["span"]:
                    players[k]["span"] = r["span"]

        print(f"  📦 {len(players)} unique (player, team) combinations")

        # ---- Step 2: Aggregate into Player dicts grouped by team ----
        teams_map: Dict[str, List[Dict]] = {}

        for (name, team_code), pd_data in players.items():
            if team_code in ("UNK", "UNKNOWN", "") or not team_code:
                continue

            teams_map.setdefault(team_code, [])

            tot_bi, tot_boi = 0, 0
            w_bavg, w_bsr = 0.0, 0.0
            w_boavg, w_bosr, w_econ = 0.0, 0.0, 0.0
            tot_mat, tot_runs, tot_wkts = 0, 0, 0

            for fmt, fs in pd_data["formats"].items():
                bat = fs.get("bat", {})
                bowl = fs.get("bowl", {})
                bi = bat.get("innings", 0)
                boi = bowl.get("innings", 0)
                tot_bi += bi
                tot_boi += boi
                tot_mat += max(bat.get("matches", 0), bowl.get("matches", 0))
                tot_runs += bat.get("runs", 0)
                tot_wkts += bowl.get("wickets", 0)
                w_bavg += bat.get("batting_avg", 0) * bi
                w_bsr += bat.get("batting_sr", 0) * bi
                w_boavg += bowl.get("bowling_avg", 0) * boi
                w_bosr += bowl.get("bowling_sr", 0) * boi
                w_econ += bowl.get("economy", 0) * boi

            batting_avg = round(w_bavg / tot_bi, 2) if tot_bi else 0.0
            batting_sr = round(w_bsr / tot_bi, 2) if tot_bi else 0.0
            bowling_avg = round(w_boavg / tot_boi, 2) if tot_boi else 99.0
            bowling_sr = round(w_bosr / tot_boi, 2) if tot_boi else 0.0
            economy = round(w_econ / tot_boi, 2) if tot_boi else 6.0

            # Form from recency
            span = pd_data.get("span", "")
            is_active = False
            if span:
                m = re.search(r'(\d{4})', span.split("-")[-1] if "-" in span else span)
                if m:
                    is_active = int(m.group(1)) >= 2023

            form = 0.55 if is_active else 0.25
            if batting_avg > 45:
                form = min(1.0, form + 0.20)
            elif batting_avg > 35:
                form = min(1.0, form + 0.12)
            elif batting_avg > 25:
                form = min(1.0, form + 0.05)
            if tot_boi > 10 and bowling_avg > 0 and bowling_avg < 25:
                form = min(1.0, form + 0.10)

            # Role
            role = cfg.classify_player_role(batting_avg, bowling_avg, tot_bi, tot_boi)

            # Wicketkeeper / Captain overrides
            is_wk = False
            keepers = cfg.KNOWN_WICKETKEEPERS.get(team_code, [])
            for k in keepers:
                parts = k.split()
                if name == k or (len(parts) > 1 and name.endswith(parts[-1]) and name[0] == parts[0][0]):
                    is_wk = True
                    role = "Wicketkeeper"
                    break

            is_capt = False
            captains = cfg.KNOWN_CAPTAINS.get(team_code, [])
            for c in captains:
                parts = c.split()
                if name == c or (len(parts) > 1 and name.endswith(parts[-1]) and name[0] == parts[0][0]):
                    is_capt = True
                    break

            pid = re.sub(r'[^a-z0-9_]', '', name.lower().replace(' ', '_'))
            teams_map[team_code].append({
                "player_id": f"{pid}_{team_code.lower()}",
                "name": name,
                "team": team_code,
                "role": role,
                "batting_avg": batting_avg,
                "batting_sr": batting_sr,
                "bowling_avg": bowling_avg,
                "bowling_sr": bowling_sr,
                "economy": economy,
                "recent_form": round(form, 2),
                "experience": tot_mat,
                "is_captain": is_capt,
                "is_wicketkeeper": is_wk,
            })

        # ---- Step 3: Build Team objects ----
        result: Dict[str, Team] = {}
        for tc, plist in teams_map.items():
            tname = cfg.TEAM_CODE_TO_NAME.get(tc, tc)
            try:
                result[tc] = Team.from_dict({
                    "team_id": tc,
                    "name": tname,
                    "country": tname,
                    "format_rankings": {},
                    "players": plist,
                    "home_advantage": cfg.HOME_ADVANTAGE.get(tc, cfg.DEFAULT_HOME_ADVANTAGE),
                })
            except Exception as e:
                logger.error(f"  Team build error [{tc}]: {e}")

        return result

    # ================================================================
    #  CACHE MANAGEMENT
    # ================================================================

    def load_cached_data(self, cache_file: Path = None) -> Optional[Dict]:
        """Load raw JSON from cache. Returns dict or None if expired/missing."""
        cf = cache_file or self.teams_file
        if not cf.exists():
            return None
        age = time.time() - cf.stat().st_mtime
        if age > self.cache_duration:
            logger.info("Cache expired")
            return None
        try:
            with open(cf, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Cache read error: {e}")
            return None

    def save_to_cache(self, teams: Dict[str, Team], cache_file: Path = None):
        """Serialize teams to JSON cache."""
        cf = cache_file or self.teams_file
        try:
            data = {tid: t.to_dict() for tid, t in teams.items()}
            with open(cf, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=1, ensure_ascii=False)
            logger.info(f"Cached {len(teams)} teams → {cf}")
        except Exception as e:
            logger.error(f"Cache write error: {e}")

    # ================================================================
    #  PUBLIC INTERFACE
    # ================================================================

    def collect_all_data(self) -> Dict[str, Team]:
        """
        Main entry point.
        Fallback chain: cache → Statsguru scrape → sample data.
        Returns dict of team_code → Team.
        """
        # Try cache
        cached = self.load_cached_data()
        if cached:
            logger.info("Loading teams from cache")
            teams = {}
            for tid, tdata in cached.items():
                try:
                    teams[tid] = Team.from_dict(tdata)
                except Exception:
                    continue
            if teams:
                return teams

        # Dependency check
        if not HAS_PANDAS:
            logger.warning("pandas required for scraping — falling back to sample data")
            logger.warning("Install with:  pip install pandas lxml beautifulsoup4")
            return self._fallback_sample()

        # ---- FULL SCRAPE ----
        print()
        print("=" * 66)
        print("  ESPN Cricinfo Statsguru - Complete Historical Data Scrape")
        print("  All teams - All players - All formats - Since 1877")
        print("=" * 66)

        all_bat: Dict[str, List] = {}
        all_bowl: Dict[str, List] = {}

        for fmt_name, fmt_class in [("Test", 1), ("ODI", 2), ("T20", 3)]:
            print(f"\n{'─' * 56}")
            print(f"  📋 {fmt_name} International Cricket")
            print(f"{'─' * 56}")
            all_bat[fmt_name] = self._scrape_all_pages(fmt_class, "batting",
                                                        f"{fmt_name} Batting")
            all_bowl[fmt_name] = self._scrape_all_pages(fmt_class, "bowling",
                                                         f"{fmt_name} Bowling")

        print(f"\n{'─' * 56}")
        print("  🔧 Merging data & building team database…")
        print(f"{'─' * 56}")
        teams = self._merge_and_build(all_bat, all_bowl)

        if teams:
            self.save_to_cache(teams)
            tp = sum(len(t.players) for t in teams.values())
            print()
            print("=" * 66)
            print(f"  ✅  {len(teams)} teams collected")
            print(f"  ✅  {tp:,} total players")
            print(f"  ✅  {self.request_count} HTTP requests made")
            print(f"  ✅  Cached → {self.teams_file}")
            print("=" * 66)
        else:
            print("\n  ❌ Scraping returned no data — falling back to sample data")
            teams = self._fallback_sample()

        return teams

    def update_live_data(self):
        """Force-refresh: delete cache so next collect_all_data() re-scrapes."""
        if self.teams_file.exists():
            self.teams_file.unlink()
            logger.info("Cache cleared — will re-scrape on next load")
        print("Cache cleared. Run 'teams' or 'match' to trigger a fresh scrape.")

    def _fallback_sample(self) -> Dict[str, Team]:
        from .models import load_sample_data
        teams = load_sample_data()
        self.save_to_cache(teams)
        return teams

    def load_sample_data(self) -> Dict[str, Team]:
        return self._fallback_sample()


# ================================================================
#  CLI STANDALONE TEST
# ================================================================

def main():
    logging.basicConfig(level=logging.INFO)
    collector = CricketDataCollector()
    teams = collector.collect_all_data()
    print(f"\nLoaded {len(teams)} teams:")
    for tid, team in sorted(teams.items(), key=lambda x: len(x[1].players), reverse=True)[:30]:
        print(f"  {tid:5s}  {team.name:25s}  {len(team.players):4d} players")
    print("  …")


if __name__ == "__main__":
    main()