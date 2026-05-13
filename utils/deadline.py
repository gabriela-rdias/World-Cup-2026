"""
utils/deadline.py — Prediction deadline enforcement (Fix #1).
Checks whether predictions are still open for a given match,
based on the room's deadline_type setting.
"""
from datetime import datetime, timedelta
from models import DeadlineType


def is_prediction_open(match_dict: dict, room_dict: dict) -> tuple[bool, str]:
    """
    Returns (is_open, reason_string).
    match_dict must have: status, kickoff_time
    room_dict  must have: deadline_type, fixed_window_hours
    """
    status = match_dict.get("status", "SCHEDULED")

    # Always closed if already finished or live
    if status == "FINISHED":
        return False, "Match has finished"
    if status in ("IN_PLAY", "PAUSED"):
        return False, "Match is live"

    kickoff = match_dict.get("kickoff_time")
    if kickoff is None:
        return True, ""  # No kickoff set yet — allow predictions

    if isinstance(kickoff, str):
        try:
            kickoff = datetime.fromisoformat(kickoff.replace("Z", ""))
        except Exception:
            return True, ""

    now = datetime.utcnow()
    deadline_type = room_dict.get("deadline_type", DeadlineType.HOUR_BEFORE)

    if deadline_type == DeadlineType.HOUR_BEFORE:
        deadline = kickoff - timedelta(hours=1)
        if now >= deadline:
            return False, f"Deadline passed (1h before kickoff at {kickoff.strftime('%H:%M')})"

    elif deadline_type == DeadlineType.DAY_BEFORE:
        deadline = kickoff.replace(hour=0, minute=0, second=0) - timedelta(seconds=1)
        if now >= deadline:
            return False, f"Deadline passed (day before {kickoff.strftime('%d %b')})"

    elif deadline_type == DeadlineType.FIXED_WINDOW:
        # Fixed window is relative to when the matchup was announced.
        # We approximate using kickoff - fixed_window_hours as a proxy.
        hours = room_dict.get("fixed_window_hours", 24)
        deadline = kickoff - timedelta(hours=hours)
        if now >= deadline:
            return False, f"Fixed deadline passed ({hours}h before kickoff)"

    return True, ""


def prediction_deadline_label(match_dict: dict, room_dict: dict) -> str:
    """Human-readable label showing when the deadline is."""
    kickoff = match_dict.get("kickoff_time")
    if kickoff is None:
        return "Deadline: TBD"

    if isinstance(kickoff, str):
        try:
            kickoff = datetime.fromisoformat(kickoff.replace("Z", ""))
        except Exception:
            return "Deadline: TBD"

    deadline_type = room_dict.get("deadline_type", DeadlineType.HOUR_BEFORE)

    if deadline_type == DeadlineType.HOUR_BEFORE:
        d = kickoff - timedelta(hours=1)
    elif deadline_type == DeadlineType.DAY_BEFORE:
        d = kickoff.replace(hour=0, minute=0, second=0) - timedelta(seconds=1)
    else:
        hours = room_dict.get("fixed_window_hours", 24)
        d = kickoff - timedelta(hours=hours)

    return f"Closes {d.strftime('%d %b %H:%M')} UTC"
