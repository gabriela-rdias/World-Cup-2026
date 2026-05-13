"""
utils/predictions.py
--------------------
CRUD operations for all prediction types:
  - Match result predictions
  - Group stage standing predictions
  - Tournament winner predictions
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from models import (
    Match, MatchPrediction, GroupStagePrediction,
    TournamentWinnerPrediction, Room
)
from utils.rooms import is_prediction_open


# ─────────────────────────────────────────────
# MATCH PREDICTIONS
# ─────────────────────────────────────────────

def upsert_match_prediction(
    db: Session,
    user_id: int,
    match_id: int,
    room_id: int,
    predicted_result: str,
) -> tuple[bool, str]:
    """
    Create or update a match prediction.
    Returns (success, message).
    """
    if predicted_result not in ("home", "draw", "away"):
        return False, "Invalid prediction value."

    match: Optional[Match] = db.get(Match, match_id)
    if not match:
        return False, "Match not found."

    # Check if match is already finished
    if match.status == "FINISHED":
        return False, "Match is already finished. Predictions are closed."

    # Check room deadline
    room: Optional[Room] = db.get(Room, room_id)
    if room and match.kickoff_time:
        if not is_prediction_open(room, match.kickoff_time):
            return False, "Prediction deadline has passed for this match."

    # Upsert
    pred = (
        db.query(MatchPrediction)
        .filter(
            MatchPrediction.user_id  == user_id,
            MatchPrediction.match_id == match_id,
            MatchPrediction.room_id  == room_id,
        )
        .first()
    )

    if pred:
        if pred.is_scored:
            return False, "This match has already been scored."
        pred.predicted_result = predicted_result
        pred.updated_at       = datetime.utcnow()
        msg = "Prediction updated!"
    else:
        pred = MatchPrediction(
            user_id          = user_id,
            match_id         = match_id,
            room_id          = room_id,
            predicted_result = predicted_result,
        )
        db.add(pred)
        msg = "Prediction saved!"

    db.commit()
    return True, msg


def get_user_match_predictions(
    db: Session, user_id: int, room_id: int
) -> dict[int, str]:
    """
    Return a dict mapping match_id -> predicted_result for the given user/room.
    """
    preds = (
        db.query(MatchPrediction)
        .filter(
            MatchPrediction.user_id == user_id,
            MatchPrediction.room_id == room_id,
        )
        .all()
    )
    return {p.match_id: p.predicted_result for p in preds}


def get_match_predictions_by_room(
    db: Session, match_id: int, room_id: int
) -> list[dict]:
    """
    Return all predictions for a match in a room, including username.
    Used to show friends' predictions on the match detail view.
    """
    from models import User
    results = (
        db.query(MatchPrediction, User)
        .join(User, MatchPrediction.user_id == User.id)
        .filter(
            MatchPrediction.match_id == match_id,
            MatchPrediction.room_id  == room_id,
        )
        .all()
    )
    return [
        {
            "username":        u.username,
            "avatar_emoji":    u.avatar_emoji,
            "predicted_result": p.predicted_result,
            "points_awarded":  p.points_awarded,
            "is_scored":       p.is_scored,
        }
        for p, u in results
    ]


# ─────────────────────────────────────────────
# GROUP STANDING PREDICTIONS
# ─────────────────────────────────────────────

def upsert_group_predictions(
    db: Session,
    user_id: int,
    room_id: int,
    group_letter: str,
    ordered_team_ids: list[int],  # Indices 0-3 → positions 1-4
) -> tuple[bool, str]:
    """
    Save a user's predicted finishing order for a group.
    ordered_team_ids should be a list of 4 team IDs in predicted order (1st → 4th).
    """
    if len(ordered_team_ids) != 4 or len(set(ordered_team_ids)) != 4:
        return False, "Must provide exactly 4 unique teams."

    # Delete existing predictions for this user/room/group
    db.query(GroupStagePrediction).filter(
        GroupStagePrediction.user_id      == user_id,
        GroupStagePrediction.room_id      == room_id,
        GroupStagePrediction.group_letter == group_letter,
        GroupStagePrediction.is_scored    == False,
    ).delete()

    for position, team_id in enumerate(ordered_team_ids, start=1):
        pred = GroupStagePrediction(
            user_id           = user_id,
            room_id           = room_id,
            group_letter      = group_letter,
            team_id           = team_id,
            predicted_position = position,
        )
        db.add(pred)

    db.commit()
    return True, f"Group {group_letter} predictions saved!"


def get_user_group_predictions(
    db: Session, user_id: int, room_id: int, group_letter: str
) -> list[int]:
    """
    Return the user's predicted team order for a group as a list of team_ids
    sorted by predicted_position ascending (1st → 4th).
    """
    preds = (
        db.query(GroupStagePrediction)
        .filter(
            GroupStagePrediction.user_id      == user_id,
            GroupStagePrediction.room_id      == room_id,
            GroupStagePrediction.group_letter == group_letter,
        )
        .order_by(GroupStagePrediction.predicted_position)
        .all()
    )
    return [p.team_id for p in preds]


# ─────────────────────────────────────────────
# TOURNAMENT WINNER PREDICTIONS
# ─────────────────────────────────────────────

def upsert_winner_prediction(
    db: Session, user_id: int, room_id: int, team_id: int
) -> tuple[bool, str]:
    """Save or update a user's tournament winner prediction."""
    pred = (
        db.query(TournamentWinnerPrediction)
        .filter(
            TournamentWinnerPrediction.user_id == user_id,
            TournamentWinnerPrediction.room_id == room_id,
        )
        .first()
    )

    if pred:
        if pred.is_scored:
            return False, "Tournament winner prediction already scored."
        pred.team_id = team_id
        msg = "Winner prediction updated!"
    else:
        pred = TournamentWinnerPrediction(
            user_id = user_id,
            room_id = room_id,
            team_id = team_id,
        )
        db.add(pred)
        msg = "Winner prediction saved! 🏆"

    db.commit()
    return True, msg


def get_winner_prediction(
    db: Session, user_id: int, room_id: int
) -> Optional[int]:
    """Return the team_id of the user's winner prediction, or None."""
    pred = (
        db.query(TournamentWinnerPrediction)
        .filter(
            TournamentWinnerPrediction.user_id == user_id,
            TournamentWinnerPrediction.room_id == room_id,
        )
        .first()
    )
    return pred.team_id if pred else None
