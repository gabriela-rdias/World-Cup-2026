"""
scoring.py — Scoring engine for the FIFA World Cup 2026 prediction game.

Point allocation:
  Group stage match:      1 pt
  Round of 32:            2 pts
  Round of 16:            4 pts
  Quarter-finals:         6 pts
  Semi-finals:            8 pts
  Final:                  10 pts
  Group standings:        1 pt (≥2 correct) / 3 pts (all 4 correct)
  Tournament winner:      15 pts
"""
from __future__ import annotations
import logging
from sqlalchemy import func
from sqlalchemy.orm import Session
from models import (
    Match, MatchPrediction, GroupStagePrediction,
    TournamentWinnerPrediction, RoomMember, MatchStage, User
)

logger = logging.getLogger(__name__)

STAGE_POINTS: dict[str, int] = {
    MatchStage.GROUP:       1,
    MatchStage.ROUND_OF_32: 2,
    MatchStage.ROUND_OF_16: 4,
    MatchStage.QUARTER:     6,
    MatchStage.SEMI:        8,
    MatchStage.THIRD_PLACE: 0,
    MatchStage.FINAL:       10,
}
WINNER_POINTS       = 15
GROUP_STANDINGS_ALL = 3
GROUP_STANDINGS_TWO = 1


# ── Match prediction scoring ──────────────────────────────────────────
def score_match_predictions(db: Session, match: Match) -> int:
    if match.result is None or match.status != "FINISHED":
        return 0
    pts_per_correct = STAGE_POINTS.get(match.stage, 1)
    preds = (db.query(MatchPrediction)
               .filter(MatchPrediction.match_id == match.id,
                       MatchPrediction.is_scored == False).all())
    for pred in preds:
        pts = pts_per_correct if pred.predicted_result == match.result else 0
        pred.points_awarded = pts
        pred.is_scored = True
        if pts > 0:
            _add_points_to_member(db, pred.user_id, pred.room_id, pts)
    db.flush()
    return len(preds)


# ── Group standings scoring ───────────────────────────────────────────
def score_group_standings(db: Session, group_letter: str, room_id: int) -> int:
    from utils.standings import compute_group_standings
    actual = compute_group_standings(db, group_letter)
    if not actual:
        return 0
    preds = (db.query(GroupStagePrediction)
               .filter(GroupStagePrediction.group_letter == group_letter,
                       GroupStagePrediction.room_id == room_id,
                       GroupStagePrediction.is_scored == False).all())
    user_preds: dict[int, list[GroupStagePrediction]] = {}
    for p in preds:
        user_preds.setdefault(p.user_id, []).append(p)
    for user_id, upreds in user_preds.items():
        correct = sum(1 for p in upreds if actual.get(p.team_id) == p.predicted_position)
        pts = GROUP_STANDINGS_ALL if correct == 4 else (GROUP_STANDINGS_TWO if correct >= 2 else 0)
        for p in upreds:
            p.is_scored = True
        upreds[0].points_awarded = pts
        if pts > 0:
            _add_points_to_member(db, user_id, room_id, pts)
    db.flush()
    return len(preds)


# ── Tournament winner scoring ─────────────────────────────────────────
def score_tournament_winner(db: Session, winning_team_id: int, room_id: int) -> int:
    preds = (db.query(TournamentWinnerPrediction)
               .filter(TournamentWinnerPrediction.room_id == room_id,
                       TournamentWinnerPrediction.is_scored == False).all())
    for pred in preds:
        pts = WINNER_POINTS if pred.team_id == winning_team_id else 0
        pred.points_awarded = pts
        pred.is_scored = True
        if pts > 0:
            _add_points_to_member(db, pred.user_id, room_id, pts)
    db.flush()
    return len(preds)


# ── Leaderboard — Fix #2: single aggregated query per category ────────
def get_leaderboard(db: Session, room_id: int) -> list[dict]:
    """
    Efficient leaderboard using aggregated SQL queries instead of N+1 loops.
    """
    # All members
    members = (db.query(RoomMember, User)
                 .join(User, RoomMember.user_id == User.id)
                 .filter(RoomMember.room_id == room_id).all())
    if not members:
        return []

    user_ids = [u.id for _, u in members]

    # Aggregate match points in one query
    match_rows = (db.query(MatchPrediction.user_id,
                            func.sum(MatchPrediction.points_awarded).label("pts"))
                    .filter(MatchPrediction.room_id == room_id,
                            MatchPrediction.is_scored == True,
                            MatchPrediction.user_id.in_(user_ids))
                    .group_by(MatchPrediction.user_id).all())
    match_pts = {r.user_id: float(r.pts or 0) for r in match_rows}

    # Aggregate group points — only rows where points_awarded > 0 (representative rows)
    group_rows = (db.query(GroupStagePrediction.user_id,
                            func.sum(GroupStagePrediction.points_awarded).label("pts"))
                    .filter(GroupStagePrediction.room_id == room_id,
                            GroupStagePrediction.is_scored == True,
                            GroupStagePrediction.points_awarded > 0,
                            GroupStagePrediction.user_id.in_(user_ids))
                    .group_by(GroupStagePrediction.user_id).all())
    group_pts = {r.user_id: float(r.pts or 0) for r in group_rows}

    # Winner points
    winner_rows = (db.query(TournamentWinnerPrediction.user_id,
                             TournamentWinnerPrediction.points_awarded)
                     .filter(TournamentWinnerPrediction.room_id == room_id,
                             TournamentWinnerPrediction.is_scored == True,
                             TournamentWinnerPrediction.user_id.in_(user_ids)).all())
    winner_pts = {r.user_id: float(r.points_awarded or 0) for r in winner_rows}

    leaderboard = []
    for member, user in members:
        uid   = user.id
        mp    = match_pts.get(uid, 0.0)
        gp    = group_pts.get(uid, 0.0)
        wp    = winner_pts.get(uid, 0.0)
        total = mp + gp + wp
        leaderboard.append({
            "user_id":      uid,
            "username":     user.username,
            "avatar_emoji": user.avatar_emoji,
            "match_points":  mp,
            "group_points":  gp,
            "winner_points": wp,
            "total_points":  total,
        })

    leaderboard.sort(key=lambda x: (-x["total_points"], x["username"]))
    rank = 1
    for i, entry in enumerate(leaderboard):
        if i > 0 and entry["total_points"] < leaderboard[i-1]["total_points"]:
            rank = i + 1
        entry["rank"] = rank

    return leaderboard


# ── Recalculate all points ────────────────────────────────────────────
def recalculate_all_points(db: Session, room_id: int):
    """Rebuild cached total_points from scored predictions."""
    members = db.query(RoomMember).filter(RoomMember.room_id == room_id).all()
    for m in members:
        m.total_points = 0.0
    for entry in get_leaderboard(db, room_id):
        m = (db.query(RoomMember)
               .filter(RoomMember.room_id == room_id,
                       RoomMember.user_id == entry["user_id"]).first())
        if m:
            m.total_points = entry["total_points"]
    db.flush()


# ── Prediction stats for social layer ────────────────────────────────
def get_match_prediction_stats(db: Session, match_id: int, room_id: int) -> dict:
    """
    Fix #5: Returns prediction counts per outcome for a match in a room.
    Used to show 'X of Y members have predicted this match'.
    """
    rows = (db.query(MatchPrediction.predicted_result,
                     func.count(MatchPrediction.id).label("cnt"))
              .filter(MatchPrediction.match_id == match_id,
                      MatchPrediction.room_id == room_id)
              .group_by(MatchPrediction.predicted_result).all())
    stats = {"home": 0, "draw": 0, "away": 0, "total": 0}
    for r in rows:
        stats[r.predicted_result] = r.cnt
        stats["total"] += r.cnt
    return stats


# ── Prediction completion stats ───────────────────────────────────────
def get_prediction_completion(db: Session, user_id: int, room_id: int) -> dict:
    """
    Fix #6: Returns prediction completion stats for a user in a room.
    {total_matches, predicted_matches, pct, total_groups, predicted_groups}
    """
    total_matches = db.query(Match).filter(Match.stage != MatchStage.THIRD_PLACE).count()
    predicted_matches = (db.query(MatchPrediction)
                           .filter(MatchPrediction.user_id == user_id,
                                   MatchPrediction.room_id == room_id).count())
    from models import Team
    total_groups = (db.query(func.count(func.distinct(Team.group_letter)))
                      .filter(Team.group_letter != "").scalar() or 0)
    predicted_groups = (db.query(func.count(func.distinct(GroupStagePrediction.group_letter)))
                          .filter(GroupStagePrediction.user_id == user_id,
                                  GroupStagePrediction.room_id == room_id).scalar() or 0)
    pct = (predicted_matches / total_matches * 100) if total_matches else 0
    return {
        "total_matches":     total_matches,
        "predicted_matches": predicted_matches,
        "total_groups":      total_groups,
        "predicted_groups":  predicted_groups,
        "pct":               pct,
    }


# ── Internal helper ───────────────────────────────────────────────────
def _add_points_to_member(db: Session, user_id: int, room_id: int, pts: float):
    m = (db.query(RoomMember)
           .filter(RoomMember.room_id == room_id,
                   RoomMember.user_id == user_id).first())
    if m:
        m.total_points = (m.total_points or 0.0) + pts
