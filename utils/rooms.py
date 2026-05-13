"""
utils/rooms.py
--------------
Room creation, joining, and management helpers.
"""

import random
import string
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from models import Room, RoomMember, User, DeadlineType


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────


def _room_to_dict(room) -> dict:
    """Convert a Room ORM object to a plain dict safe for session_state."""
    return {
        "id":                  room.id,
        "name":               room.name,
        "invite_code":        room.invite_code,
        "owner_id":           room.owner_id,
        "deadline_type":      room.deadline_type,
        "fixed_window_hours": room.fixed_window_hours or 24,
        "description":        room.description or "",
    }


def generate_invite_code(length: int = 8) -> str:
    """Generate a random alphanumeric invite code (uppercase)."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def create_room(
    db: Session,
    name: str,
    owner: User,
    description: str = "",
    deadline_type: str = DeadlineType.HOUR_BEFORE,
    fixed_window_hours: int = 24,
) -> tuple[bool, str, Optional[Room]]:
    """
    Create a new prediction room.
    The owner is automatically added as a member.
    Returns (success, message, room_or_None).
    """
    name = name.strip()
    if len(name) < 3:
        return False, "Room name must be at least 3 characters.", None

    # Generate a unique invite code
    for _ in range(10):
        code = generate_invite_code()
        if not db.query(Room).filter(Room.invite_code == code).first():
            break
    else:
        return False, "Failed to generate unique invite code. Try again.", None

    room = Room(
        name               = name,
        invite_code        = code,
        owner_id           = owner.id,
        description        = description.strip(),
        deadline_type      = deadline_type,
        fixed_window_hours = fixed_window_hours,
    )
    db.add(room)
    db.flush()  # Get the room.id before adding member

    # Auto-add owner as first member
    membership = RoomMember(room_id=room.id, user_id=owner.id)
    db.add(membership)
    db.commit()
    db.refresh(room)
    room_dict = _room_to_dict(room)
    return True, f"Room '{name}' created! Invite code: {code}", room_dict


def join_room(
    db: Session,
    invite_code: str,
    user: User,
) -> tuple[bool, str, Optional[Room]]:
    """
    Add a user to a room by invite code.
    Returns (success, message, room_or_None).
    """
    invite_code = invite_code.strip().upper()
    room = db.query(Room).filter(Room.invite_code == invite_code, Room.is_active == True).first()

    if not room:
        return False, "Room not found. Check the invite code.", None

    existing = (
        db.query(RoomMember)
        .filter(RoomMember.room_id == room.id, RoomMember.user_id == user.id)
        .first()
    )
    if existing:
        return False, "You are already a member of this room.", _room_to_dict(room)

    membership = RoomMember(room_id=room.id, user_id=user.id)
    db.add(membership)
    db.commit()
    return True, f"You have joined room '{room.name}'!", _room_to_dict(room)


def get_user_rooms(db: Session, user_id: int) -> list[Room]:
    """Return all active rooms the user belongs to."""
    return (
        db.query(Room)
        .join(RoomMember, Room.id == RoomMember.room_id)
        .filter(RoomMember.user_id == user_id, Room.is_active == True)
        .order_by(Room.created_at.desc())
        .all()
    )


def get_room_members(db: Session, room_id: int) -> list[RoomMember]:
    """Return all members of a room, ordered by total points descending."""
    return (
        db.query(RoomMember)
        .filter(RoomMember.room_id == room_id)
        .order_by(RoomMember.total_points.desc())
        .all()
    )


# ─────────────────────────────────────────────
# DEADLINE LOGIC
# ─────────────────────────────────────────────

def is_prediction_open(room: Room, kickoff_time: Optional[datetime]) -> bool:
    """
    Determine whether a prediction is still open for a given match kickoff time,
    based on the room's deadline settings.
    """
    if kickoff_time is None:
        return True  # No kickoff time known yet → allow predictions

    now = datetime.utcnow()

    if room.deadline_type == DeadlineType.HOUR_BEFORE:
        deadline = kickoff_time - timedelta(hours=1)
    elif room.deadline_type == DeadlineType.DAY_BEFORE:
        deadline = kickoff_time.replace(hour=0, minute=0, second=0) - timedelta(days=1)
    elif room.deadline_type == DeadlineType.FIXED_WINDOW:
        # Fixed window: predictions close N hours after matchup was known
        # For simplicity, we treat FIXED_WINDOW the same as HOUR_BEFORE
        deadline = kickoff_time - timedelta(hours=room.fixed_window_hours or 24)
    else:
        deadline = kickoff_time - timedelta(hours=1)

    return now < deadline


def deadline_text(room: Room, kickoff_time: Optional[datetime]) -> str:
    """Return a human-readable description of the prediction deadline."""
    if room.deadline_type == DeadlineType.HOUR_BEFORE:
        return "Predictions close 1 hour before kickoff"
    elif room.deadline_type == DeadlineType.DAY_BEFORE:
        return "Predictions close the day before the match"
    elif room.deadline_type == DeadlineType.FIXED_WINDOW:
        return f"Predictions close {room.fixed_window_hours}h after matchups are announced"
    return "Unknown deadline"
