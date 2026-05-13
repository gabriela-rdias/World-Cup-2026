"""
utils/standings.py
------------------
Compute group stage standings from finished matches stored in the local DB.
Used by the scoring engine and the standings display page.
"""

from sqlalchemy.orm import Session
from models import Match, Team, MatchStage


def compute_group_standings(db: Session, group_letter: str) -> dict[int, int]:
    """
    Calculate final group standings from finished group-stage matches.
    Returns a dict mapping team_id -> position (1-indexed, 1 = first).
    """
    # Gather all finished group matches for this group
    matches: list[Match] = (
        db.query(Match)
        .filter(
            Match.stage == MatchStage.GROUP,
            Match.group_letter == group_letter,
            Match.status == "FINISHED",
        )
        .all()
    )

    if not matches:
        return {}

    # Collect all team IDs in this group
    team_ids: set[int] = set()
    for m in matches:
        if m.home_team_id:
            team_ids.add(m.home_team_id)
        if m.away_team_id:
            team_ids.add(m.away_team_id)

    # Build stats dict: team_id -> {pts, gd, gf}
    stats: dict[int, dict] = {
        tid: {"pts": 0, "gd": 0, "gf": 0, "played": 0}
        for tid in team_ids
    }

    for m in matches:
        if m.home_score is None or m.away_score is None:
            continue

        hs, as_ = m.home_score, m.away_score
        h, a    = m.home_team_id, m.away_team_id

        if h not in stats or a not in stats:
            continue

        stats[h]["gf"]     += hs
        stats[h]["gd"]     += hs - as_
        stats[h]["played"] += 1
        stats[a]["gf"]     += as_
        stats[a]["gd"]     += as_ - hs
        stats[a]["played"] += 1

        if hs > as_:
            stats[h]["pts"] += 3
        elif as_ > hs:
            stats[a]["pts"] += 3
        else:
            stats[h]["pts"] += 1
            stats[a]["pts"] += 1

    # Sort: points → goal difference → goals for
    ranked = sorted(
        team_ids,
        key=lambda tid: (
            -stats[tid]["pts"],
            -stats[tid]["gd"],
            -stats[tid]["gf"],
        ),
    )

    return {tid: pos + 1 for pos, tid in enumerate(ranked)}


def get_full_group_table(db: Session, group_letter: str) -> list[dict]:
    """
    Return a list of dicts representing the group table, sorted by standing.
    Each dict contains: position, team_id, team_name, played, won, draw, lost,
    goals_for, goals_against, goal_difference, points.
    """
    matches: list[Match] = (
        db.query(Match)
        .filter(
            Match.stage == MatchStage.GROUP,
            Match.group_letter == group_letter,
        )
        .all()
    )

    # Collect teams
    team_ids: set[int] = set()
    for m in matches:
        if m.home_team_id:
            team_ids.add(m.home_team_id)
        if m.away_team_id:
            team_ids.add(m.away_team_id)

    stats: dict[int, dict] = {
        tid: {"pts": 0, "gd": 0, "gf": 0, "ga": 0, "won": 0, "draw": 0, "lost": 0, "played": 0}
        for tid in team_ids
    }

    for m in matches:
        if m.status != "FINISHED" or m.home_score is None or m.away_score is None:
            continue

        hs, as_ = m.home_score, m.away_score
        h, a    = m.home_team_id, m.away_team_id

        for tid in (h, a):
            if tid not in stats:
                continue

        # Home stats
        if h in stats:
            stats[h]["gf"]     += hs
            stats[h]["ga"]     += as_
            stats[h]["gd"]     += hs - as_
            stats[h]["played"] += 1

        # Away stats
        if a in stats:
            stats[a]["gf"]     += as_
            stats[a]["ga"]     += hs
            stats[a]["gd"]     += as_ - hs
            stats[a]["played"] += 1

        if hs > as_:
            if h in stats: stats[h]["pts"] += 3; stats[h]["won"] += 1
            if a in stats: stats[a]["lost"] += 1
        elif as_ > hs:
            if a in stats: stats[a]["pts"] += 3; stats[a]["won"] += 1
            if h in stats: stats[h]["lost"] += 1
        else:
            if h in stats: stats[h]["pts"] += 1; stats[h]["draw"] += 1
            if a in stats: stats[a]["pts"] += 1; stats[a]["draw"] += 1

    # Build table rows with team names
    rows = []
    for tid in team_ids:
        team = db.get(Team, tid)
        team_name = team.name if team else f"Team {tid}"
        rows.append({
            "team_id":          tid,
            "team_name":        team_name,
            **stats[tid],
        })

    # Sort: points → GD → GF
    rows.sort(key=lambda r: (-r["pts"], -r["gd"], -r["gf"]))
    for i, r in enumerate(rows):
        r["position"] = i + 1

    return rows
