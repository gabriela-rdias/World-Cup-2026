"""
api/football_api.py
-------------------
Wrapper around the Football-Data.org free API (v4).
Provides methods for fetching teams, matches, standings, and recent results.
All responses are cached in the local SQLite database to respect rate limits.

Free tier: 10 requests/minute — caching is CRITICAL.
API Docs:  https://www.football-data.org/documentation/quickstart
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Any

import requests
from sqlalchemy.orm import Session

from models import APICache, Team, Match, MatchStage

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

API_KEY       = os.environ.get("FOOTBALL_API_KEY", "")
BASE_URL      = "https://api.football-data.org/v4"
WC_2026_CODE  = "WC"               # Competition code on football-data.org
DEFAULT_TTL   = timedelta(hours=1)  # Cache TTL for most requests
RESULT_TTL    = timedelta(minutes=10)  # Shorter TTL for live/recent results
STATIC_TTL    = timedelta(hours=24)    # Long TTL for static data (teams, etc.)


def _headers() -> dict:
    return {"X-Auth-Token": API_KEY}


# ─────────────────────────────────────────────
# CACHE HELPERS
# ─────────────────────────────────────────────

def _get_cached(db: Session, key: str) -> Optional[Any]:
    """Return the parsed JSON value from cache if it exists and hasn't expired."""
    entry: Optional[APICache] = (
        db.query(APICache).filter(APICache.cache_key == key).first()
    )
    if entry and entry.expires_at > datetime.utcnow():
        return json.loads(entry.value)
    return None


def _set_cache(db: Session, key: str, value: Any, ttl: timedelta = DEFAULT_TTL):
    """Store a JSON-serialisable value in the cache."""
    serialised = json.dumps(value)
    entry = db.query(APICache).filter(APICache.cache_key == key).first()
    if entry:
        entry.value      = serialised
        entry.created_at = datetime.utcnow()
        entry.expires_at = datetime.utcnow() + ttl
    else:
        entry = APICache(
            cache_key  = key,
            value      = serialised,
            created_at = datetime.utcnow(),
            expires_at = datetime.utcnow() + ttl,
        )
        db.add(entry)
    try:
        db.commit()
    except Exception:
        db.rollback()


def _fetch(url: str, params: dict = None) -> Optional[dict]:
    """Perform a GET request to the API. Returns parsed JSON or None on error."""
    if not API_KEY:
        logger.warning("No FOOTBALL_API_KEY set — returning None for API call.")
        return None
    try:
        resp = requests.get(url, headers=_headers(), params=params, timeout=10)
        if resp.status_code == 429:
            logger.error("API rate limit hit. Relying on cached data.")
            return None
        if resp.status_code != 200:
            logger.error(f"API error {resp.status_code}: {resp.text[:200]}")
            return None
        return resp.json()
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        return None


# ─────────────────────────────────────────────
# PUBLIC API METHODS
# ─────────────────────────────────────────────

def get_competition_teams(db: Session) -> list[dict]:
    """
    Fetch all teams in the 2026 World Cup.
    Returns a list of team dicts with: id, name, shortName, tla, crest.
    """
    cache_key = "wc2026_teams"
    cached = _get_cached(db, cache_key)
    if cached:
        return cached

    data = _fetch(f"{BASE_URL}/competitions/{WC_2026_CODE}/teams")
    if not data:
        return _fallback_teams()

    teams = [
        {
            "id":        t["id"],
            "name":      t["name"],
            "shortName": t.get("shortName", t["name"]),
            "tla":       t.get("tla", ""),
            "crest":     t.get("crest", ""),
        }
        for t in data.get("teams", [])
    ]
    _set_cache(db, cache_key, teams, STATIC_TTL)
    return teams


def get_competition_matches(db: Session, matchday: int = None) -> list[dict]:
    """
    Fetch all matches (or matches for a specific matchday) from the 2026 World Cup.
    Returns a normalised list of match dicts.
    """
    cache_key = f"wc2026_matches_md{matchday or 'all'}"
    cached = _get_cached(db, cache_key)
    if cached:
        return cached

    params = {}
    if matchday:
        params["matchday"] = matchday

    data = _fetch(f"{BASE_URL}/competitions/{WC_2026_CODE}/matches", params=params)
    if not data:
        return []

    matches = []
    for m in data.get("matches", []):
        matches.append(_normalise_match(m))

    ttl = RESULT_TTL if any(m.get("status") in ("IN_PLAY", "PAUSED") for m in matches) else DEFAULT_TTL
    _set_cache(db, cache_key, matches, ttl)
    return matches


def get_team_recent_matches(db: Session, team_id: int, limit: int = 5) -> list[dict]:
    """
    Fetch the last `limit` finished matches for a team (any competition).
    Used on the Teams page to show recent form.
    """
    cache_key = f"team_{team_id}_recent_{limit}"
    cached = _get_cached(db, cache_key)
    if cached:
        return cached

    data = _fetch(
        f"{BASE_URL}/teams/{team_id}/matches",
        params={"status": "FINISHED", "limit": limit},
    )
    if not data:
        return []

    matches = [_normalise_match(m) for m in data.get("matches", [])[-limit:]]
    _set_cache(db, cache_key, matches, DEFAULT_TTL)
    return matches


def get_competition_standings(db: Session) -> list[dict]:
    """
    Fetch the current group stage standings table.
    Returns a list of group dicts, each with a 'table' list of team entries.
    """
    cache_key = "wc2026_standings"
    cached = _get_cached(db, cache_key)
    if cached:
        return cached

    data = _fetch(f"{BASE_URL}/competitions/{WC_2026_CODE}/standings")
    if not data:
        return []

    standings = []
    for group in data.get("standings", []):
        table = [
            {
                "position":       row["position"],
                "team_id":        row["team"]["id"],
                "team_name":      row["team"]["name"],
                "team_crest":     row["team"].get("crest", ""),
                "played":         row["playedGames"],
                "won":            row["won"],
                "draw":           row["draw"],
                "lost":           row["lost"],
                "goals_for":      row["goalsFor"],
                "goals_against":  row["goalsAgainst"],
                "goal_difference": row["goalDifference"],
                "points":         row["points"],
            }
            for row in group["table"]
        ]
        standings.append({
            "group":  group.get("group", ""),
            "stage":  group.get("stage", ""),
            "table":  table,
        })

    _set_cache(db, cache_key, standings, RESULT_TTL)
    return standings


def sync_matches_to_db(db: Session):
    """
    Pull all competition matches from the API and upsert them into the
    local Match table. Also syncs Team records.
    Called at startup and periodically by a background refresh.
    """
    raw_matches = get_competition_matches(db)
    if not raw_matches:
        logger.warning("No matches returned from API — DB sync skipped.")
        return

    team_cache: dict[int, Team] = {}

    for m in raw_matches:
        # ── Upsert home team ──
        for role in ("home", "away"):
            t_data = m.get(f"{role}_team")
            if not t_data or not t_data.get("id"):
                continue
            t_id = t_data["id"]
            if t_id not in team_cache:
                team = db.get(Team, t_id)
                if not team:
                    team = Team(
                        id         = t_id,
                        name       = t_data.get("name", "TBD"),
                        short_name = t_data.get("shortName", ""),
                        tla        = t_data.get("tla", ""),
                        crest_url  = t_data.get("crest", ""),
                    )
                    db.add(team)
                team_cache[t_id] = team

        # ── Upsert match ──
        match = db.get(Match, m["id"])
        if not match:
            match = Match(id=m["id"])
            db.add(match)

        match.stage         = _map_stage(m.get("stage", ""))
        match.group_letter  = m.get("group", "")[-1] if m.get("group") else ""
        match.matchday      = m.get("matchday", 0) or 0
        match.home_team_id  = m["home_team"]["id"] if m.get("home_team") and m["home_team"].get("id") else None
        match.away_team_id  = m["away_team"]["id"] if m.get("away_team") and m["away_team"].get("id") else None
        match.kickoff_time  = _parse_dt(m.get("kickoff_time"))
        match.venue         = m.get("venue", "")
        match.home_score    = m.get("home_score")
        match.away_score    = m.get("away_score")
        match.status        = m.get("status", "SCHEDULED")
        match.last_updated  = datetime.utcnow()

        # Derive result string from scores
        if match.home_score is not None and match.away_score is not None and match.status == "FINISHED":
            if match.home_score > match.away_score:
                match.result = "home"
            elif match.away_score > match.home_score:
                match.result = "away"
            else:
                match.result = "draw"

    try:
        db.commit()
        logger.info(f"Synced {len(raw_matches)} matches to DB.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error syncing matches: {e}")


# ─────────────────────────────────────────────
# NORMALISATION HELPERS
# ─────────────────────────────────────────────

def _normalise_match(m: dict) -> dict:
    """Convert a raw API match dict into a clean internal format."""
    score = m.get("score", {})
    ft    = score.get("fullTime", {})

    home_team = m.get("homeTeam", {})
    away_team = m.get("awayTeam", {})

    return {
        "id":        m["id"],
        "stage":     m.get("stage", ""),
        "group":     m.get("group", ""),
        "matchday":  m.get("matchday"),
        "status":    m.get("status", "SCHEDULED"),
        "kickoff_time": m.get("utcDate"),
        "venue":     m.get("venue", ""),
        "home_team": {
            "id":        home_team.get("id"),
            "name":      home_team.get("name", "TBD"),
            "shortName": home_team.get("shortName", "TBD"),
            "tla":       home_team.get("tla", ""),
            "crest":     home_team.get("crest", ""),
        },
        "away_team": {
            "id":        away_team.get("id"),
            "name":      away_team.get("name", "TBD"),
            "shortName": away_team.get("shortName", "TBD"),
            "tla":       away_team.get("tla", ""),
            "crest":     away_team.get("crest", ""),
        },
        "home_score": ft.get("home"),
        "away_score": ft.get("away"),
    }


def _map_stage(api_stage: str) -> str:
    """Map the API's stage string to our internal MatchStage enum value."""
    mapping = {
        "GROUP_STAGE":    MatchStage.GROUP,
        "LAST_32":        MatchStage.ROUND_OF_32,
        "LAST_16":        MatchStage.ROUND_OF_16,
        "QUARTER_FINALS": MatchStage.QUARTER,
        "SEMI_FINALS":    MatchStage.SEMI,
        "FINAL":          MatchStage.FINAL,
    }
    return mapping.get(api_stage, MatchStage.GROUP)


def _parse_dt(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse an ISO 8601 datetime string to a Python datetime object."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


# ─────────────────────────────────────────────
# FALLBACK DATA (when API key is missing)
# ─────────────────────────────────────────────

def _fallback_teams() -> list[dict]:
    """
    Return a minimal set of World Cup 2026 qualified teams for demo purposes
    when no API key is configured. These are the confirmed qualified nations
    as of early 2025.
    """
    return [
        {"id": 1,  "name": "Brazil",        "shortName": "Brazil",      "tla": "BRA", "crest": ""},
        {"id": 2,  "name": "Argentina",     "shortName": "Argentina",   "tla": "ARG", "crest": ""},
        {"id": 3,  "name": "France",        "shortName": "France",      "tla": "FRA", "crest": ""},
        {"id": 4,  "name": "England",       "shortName": "England",     "tla": "ENG", "crest": ""},
        {"id": 5,  "name": "Germany",       "shortName": "Germany",     "tla": "GER", "crest": ""},
        {"id": 6,  "name": "Spain",         "shortName": "Spain",       "tla": "ESP", "crest": ""},
        {"id": 7,  "name": "Portugal",      "shortName": "Portugal",    "tla": "POR", "crest": ""},
        {"id": 8,  "name": "Netherlands",   "shortName": "Netherlands", "tla": "NED", "crest": ""},
        {"id": 9,  "name": "USA",           "shortName": "USA",         "tla": "USA", "crest": ""},
        {"id": 10, "name": "Mexico",        "shortName": "Mexico",      "tla": "MEX", "crest": ""},
        {"id": 11, "name": "Canada",        "shortName": "Canada",      "tla": "CAN", "crest": ""},
        {"id": 12, "name": "Japan",         "shortName": "Japan",       "tla": "JPN", "crest": ""},
        {"id": 13, "name": "South Korea",   "shortName": "S. Korea",    "tla": "KOR", "crest": ""},
        {"id": 14, "name": "Morocco",       "shortName": "Morocco",     "tla": "MAR", "crest": ""},
        {"id": 15, "name": "Senegal",       "shortName": "Senegal",     "tla": "SEN", "crest": ""},
        {"id": 16, "name": "Colombia",      "shortName": "Colombia",    "tla": "COL", "crest": ""},
        {"id": 17, "name": "Uruguay",       "shortName": "Uruguay",     "tla": "URU", "crest": ""},
        {"id": 18, "name": "Ecuador",       "shortName": "Ecuador",     "tla": "ECU", "crest": ""},
        {"id": 19, "name": "Switzerland",   "shortName": "Switzerland", "tla": "SUI", "crest": ""},
        {"id": 20, "name": "Belgium",       "shortName": "Belgium",     "tla": "BEL", "crest": ""},
        {"id": 21, "name": "Croatia",       "shortName": "Croatia",     "tla": "CRO", "crest": ""},
        {"id": 22, "name": "Serbia",        "shortName": "Serbia",      "tla": "SRB", "crest": ""},
        {"id": 23, "name": "Denmark",       "shortName": "Denmark",     "tla": "DEN", "crest": ""},
        {"id": 24, "name": "Austria",       "shortName": "Austria",     "tla": "AUT", "crest": ""},
        {"id": 25, "name": "Poland",        "shortName": "Poland",      "tla": "POL", "crest": ""},
        {"id": 26, "name": "Australia",     "shortName": "Australia",   "tla": "AUS", "crest": ""},
        {"id": 27, "name": "Iran",          "shortName": "Iran",        "tla": "IRN", "crest": ""},
        {"id": 28, "name": "Saudi Arabia",  "shortName": "S. Arabia",   "tla": "KSA", "crest": ""},
        {"id": 29, "name": "Cameroon",      "shortName": "Cameroon",    "tla": "CMR", "crest": ""},
        {"id": 30, "name": "Nigeria",       "shortName": "Nigeria",     "tla": "NGA", "crest": ""},
        {"id": 31, "name": "Ghana",         "shortName": "Ghana",       "tla": "GHA", "crest": ""},
        {"id": 32, "name": "Ivory Coast",   "shortName": "C. d'Ivoire", "tla": "CIV", "crest": ""},
        {"id": 33, "name": "Venezuela",     "shortName": "Venezuela",   "tla": "VEN", "crest": ""},
        {"id": 34, "name": "Bolivia",       "shortName": "Bolivia",     "tla": "BOL", "crest": ""},
        {"id": 35, "name": "Paraguay",      "shortName": "Paraguay",    "tla": "PAR", "crest": ""},
        {"id": 36, "name": "Qatar",         "shortName": "Qatar",       "tla": "QAT", "crest": ""},
    ]
