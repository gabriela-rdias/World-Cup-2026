"""
models.py
---------
SQLAlchemy ORM model definitions for the FIFA World Cup 2026 prediction game.
Defines all database tables: users, rooms, teams, matches, predictions, etc.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float,
    ForeignKey, Text, UniqueConstraint, Enum
)
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


# ─────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────

class MatchStage(str, enum.Enum):
    GROUP       = "group"
    ROUND_OF_32 = "round_of_32"   # Round of 32 (16-avos)
    ROUND_OF_16 = "round_of_16"
    QUARTER     = "quarter_final"
    SEMI        = "semi_final"
    THIRD_PLACE = "third_place"
    FINAL       = "final"


class PredictionResult(str, enum.Enum):
    HOME = "home"   # Home team wins
    DRAW = "draw"   # Draw
    AWAY = "away"   # Away team wins


class DeadlineType(str, enum.Enum):
    FIXED_WINDOW   = "fixed_window"    # Fixed time after matchups known
    DAY_BEFORE     = "day_before"      # Until the day before the match
    HOUR_BEFORE    = "hour_before"     # Until 1 hour before kickoff


# ─────────────────────────────────────────────
# USER
# ─────────────────────────────────────────────

class User(Base):
    """Represents a registered user of the platform."""
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String(50), unique=True, nullable=False, index=True)
    email         = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    avatar_emoji  = Column(String(10), default="⚽")          # Fun avatar selection
    created_at    = Column(DateTime, default=datetime.utcnow)
    is_active     = Column(Boolean, default=True)

    # Relationships
    room_memberships  = relationship("RoomMember", back_populates="user", cascade="all, delete-orphan")
    predictions       = relationship("MatchPrediction", back_populates="user", cascade="all, delete-orphan")
    group_predictions = relationship("GroupStagePrediction", back_populates="user", cascade="all, delete-orphan")
    winner_predictions = relationship("TournamentWinnerPrediction", back_populates="user", cascade="all, delete-orphan")
    owned_rooms       = relationship("Room", back_populates="owner")

    def __repr__(self):
        return f"<User {self.username}>"


# ─────────────────────────────────────────────
# ROOM
# ─────────────────────────────────────────────

class Room(Base):
    """A private prediction room that users can create and join."""
    __tablename__ = "rooms"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(100), nullable=False)
    invite_code   = Column(String(12), unique=True, nullable=False, index=True)
    owner_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)
    description   = Column(Text, default="")
    is_active     = Column(Boolean, default=True)

    # Deadline settings chosen by the room owner
    deadline_type        = Column(String(30), default=DeadlineType.HOUR_BEFORE)
    fixed_window_hours   = Column(Integer, default=24)  # Only used if deadline_type == FIXED_WINDOW

    # Relationships
    owner   = relationship("User", back_populates="owned_rooms")
    members = relationship("RoomMember", back_populates="room", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Room {self.name} ({self.invite_code})>"


class RoomMember(Base):
    """Association table linking users to rooms (many-to-many with extra data)."""
    __tablename__ = "room_members"

    id        = Column(Integer, primary_key=True)
    room_id   = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    user_id   = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    total_points = Column(Float, default=0.0)   # Cached total for fast leaderboard

    __table_args__ = (UniqueConstraint("room_id", "user_id", name="uq_room_user"),)

    # Relationships
    room = relationship("Room", back_populates="members")
    user = relationship("User", back_populates="room_memberships")

    def __repr__(self):
        return f"<RoomMember room={self.room_id} user={self.user_id}>"


# ─────────────────────────────────────────────
# TEAM
# ─────────────────────────────────────────────

class Team(Base):
    """A national team participating in the World Cup."""
    __tablename__ = "teams"

    id           = Column(Integer, primary_key=True)   # External API ID
    name         = Column(String(100), nullable=False)
    short_name   = Column(String(10), default="")
    tla          = Column(String(5), default="")        # Three-letter abbreviation
    flag_url     = Column(String(255), default="")
    group_letter = Column(String(1), default="")        # e.g. "A", "B", ...
    crest_url    = Column(String(255), default="")

    # Relationships
    home_matches = relationship("Match", foreign_keys="Match.home_team_id", back_populates="home_team")
    away_matches = relationship("Match", foreign_keys="Match.away_team_id", back_populates="away_team")

    def __repr__(self):
        return f"<Team {self.name}>"


# ─────────────────────────────────────────────
# MATCH
# ─────────────────────────────────────────────

class Match(Base):
    """A single World Cup match (group stage or knockout)."""
    __tablename__ = "matches"

    id              = Column(Integer, primary_key=True)   # External API match ID
    stage           = Column(String(30), nullable=False)  # One of MatchStage values
    group_letter    = Column(String(1), default="")       # Only for group stage
    matchday        = Column(Integer, default=0)          # Matchday number
    home_team_id    = Column(Integer, ForeignKey("teams.id"), nullable=True)
    away_team_id    = Column(Integer, ForeignKey("teams.id"), nullable=True)
    kickoff_time    = Column(DateTime, nullable=True)
    venue           = Column(String(200), default="")
    city            = Column(String(100), default="")

    # Result (None until played)
    home_score      = Column(Integer, nullable=True)
    away_score      = Column(Integer, nullable=True)
    result          = Column(String(10), nullable=True)   # "home", "draw", "away"
    status          = Column(String(30), default="SCHEDULED")  # SCHEDULED, LIVE, FINISHED

    last_updated    = Column(DateTime, default=datetime.utcnow)

    # Relationships
    home_team   = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team   = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    predictions = relationship("MatchPrediction", back_populates="match", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Match {self.home_team_id} vs {self.away_team_id} ({self.stage})>"


# ─────────────────────────────────────────────
# PREDICTIONS
# ─────────────────────────────────────────────

class MatchPrediction(Base):
    """A user's prediction for a single match result."""
    __tablename__ = "match_predictions"

    id              = Column(Integer, primary_key=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    match_id        = Column(Integer, ForeignKey("matches.id"), nullable=False)
    room_id         = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    predicted_result = Column(String(10), nullable=False)  # "home", "draw", "away"
    points_awarded  = Column(Float, default=0.0)
    is_scored       = Column(Boolean, default=False)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "match_id", "room_id", name="uq_user_match_room"),)

    # Relationships
    user  = relationship("User", back_populates="predictions")
    match = relationship("Match", back_populates="predictions")

    def __repr__(self):
        return f"<MatchPrediction user={self.user_id} match={self.match_id} pred={self.predicted_result}>"


class GroupStagePrediction(Base):
    """
    A user's prediction for the final standings of a group.
    Stores the predicted rank (1–4) for each team in the group.
    """
    __tablename__ = "group_stage_predictions"

    id           = Column(Integer, primary_key=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    room_id      = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    group_letter = Column(String(1), nullable=False)  # "A" through "L"
    team_id      = Column(Integer, ForeignKey("teams.id"), nullable=False)
    predicted_position = Column(Integer, nullable=False)  # 1, 2, 3, or 4
    points_awarded = Column(Float, default=0.0)
    is_scored    = Column(Boolean, default=False)
    created_at   = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "room_id", "group_letter", "team_id", name="uq_group_pred"),
    )

    # Relationships
    user = relationship("User", back_populates="group_predictions")

    def __repr__(self):
        return f"<GroupStagePrediction user={self.user_id} group={self.group_letter} team={self.team_id} pos={self.predicted_position}>"


class TournamentWinnerPrediction(Base):
    """A user's pre-tournament prediction for the overall World Cup winner (15 points)."""
    __tablename__ = "tournament_winner_predictions"

    id             = Column(Integer, primary_key=True)
    user_id        = Column(Integer, ForeignKey("users.id"), nullable=False)
    room_id        = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    team_id        = Column(Integer, ForeignKey("teams.id"), nullable=False)
    points_awarded = Column(Float, default=0.0)
    is_scored      = Column(Boolean, default=False)
    created_at     = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "room_id", name="uq_winner_pred"),)

    # Relationships
    user = relationship("User", back_populates="winner_predictions")

    def __repr__(self):
        return f"<TournamentWinnerPrediction user={self.user_id} team={self.team_id}>"


# ─────────────────────────────────────────────
# CACHE (for API responses)
# ─────────────────────────────────────────────

class APICache(Base):
    """
    Simple key-value store to cache API responses and avoid hitting rate limits.
    Each entry expires after a configurable TTL.
    """
    __tablename__ = "api_cache"

    id         = Column(Integer, primary_key=True)
    cache_key  = Column(String(255), unique=True, nullable=False, index=True)
    value      = Column(Text, nullable=False)        # JSON-serialised response
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    def __repr__(self):
        return f"<APICache key={self.cache_key}>"
