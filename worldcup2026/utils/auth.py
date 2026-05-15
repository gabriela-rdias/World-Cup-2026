"""
utils/auth.py — Authentication helpers with input validation and rate limiting.
Fixes #4 (input sanitisation), #11 (session validation), #12 (login rate limiting).
"""
import re
import html
import streamlit as st
import bcrypt
from sqlalchemy.orm import Session
from models import User

# ── Constants ─────────────────────────────────────────────────────────
MAX_LOGIN_ATTEMPTS = 5
USERNAME_RE = re.compile(r'^[a-zA-Z0-9_\-\.]{3,30}$')


# ── Input sanitisation helpers (Fix #4) ──────────────────────────────
def sanitise_username(raw: str) -> str:
    """Strip whitespace; allow only safe characters."""
    return raw.strip()

def validate_username(username: str) -> tuple[bool, str]:
    if not username:
        return False, "Username is required."
    if not USERNAME_RE.match(username):
        return False, "Username must be 3–30 characters: letters, numbers, _ - . only."
    return True, ""

def validate_password(password: str) -> tuple[bool, str]:
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    return True, ""

def validate_email(email: str) -> tuple[bool, str]:
    email = email.strip()
    if "@" not in email or "." not in email.split("@")[-1]:
        return False, "Please enter a valid email address."
    return True, ""

def safe_display(text: str) -> str:
    """HTML-escape a string for safe rendering in st.markdown."""
    return html.escape(str(text))


# ── Rate limiting (Fix #12) ───────────────────────────────────────────
def _get_attempt_state() -> dict:
    if "login_attempts" not in st.session_state:
        st.session_state.login_attempts = {"count": 0, "locked": False}
    return st.session_state.login_attempts

def _record_failed_attempt() -> int:
    state = _get_attempt_state()
    state["count"] += 1
    if state["count"] >= MAX_LOGIN_ATTEMPTS:
        state["locked"] = True
    return state["count"]

def _reset_attempts():
    st.session_state.login_attempts = {"count": 0, "locked": False}

def is_login_locked() -> bool:
    return _get_attempt_state().get("locked", False)

def remaining_attempts() -> int:
    return max(0, MAX_LOGIN_ATTEMPTS - _get_attempt_state().get("count", 0))


# ── Registration ──────────────────────────────────────────────────────
def register_user(db: Session, username: str, email: str,
                  password: str, avatar: str = "Ball") -> tuple[bool, str]:
    username = sanitise_username(username)
    email    = email.strip().lower()

    ok, msg = validate_username(username)
    if not ok:
        return False, msg
    ok, msg = validate_email(email)
    if not ok:
        return False, msg
    ok, msg = validate_password(password)
    if not ok:
        return False, msg

    if db.query(User).filter(User.username == username).first():
        return False, "Username already taken."
    if db.query(User).filter(User.email == email).first():
        return False, "Email already registered."

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user = User(username=username, email=email,
                password_hash=pw_hash, avatar_emoji=avatar)
    db.add(user)
    db.commit()
    return True, "Account created successfully!"


# ── Login ─────────────────────────────────────────────────────────────
def login_user(db: Session, username: str,
               password: str) -> tuple[bool, str, dict | None]:
    """
    Returns (success, message, user_dict).
    Enforces rate limiting. Validates user still exists (Fix #11).
    """
    if is_login_locked():
        return False, "Too many failed attempts. Please restart the app.", None

    username = sanitise_username(username)
    if not username or not password:
        return False, "Please enter your username and password.", None

    user: User | None = db.query(User).filter(User.username == username).first()

    if not user or not user.is_active:
        _record_failed_attempt()
        rem = remaining_attempts()
        return False, f"Invalid username or password. {rem} attempt(s) remaining.", None

    if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        _record_failed_attempt()
        rem = remaining_attempts()
        return False, f"Invalid username or password. {rem} attempt(s) remaining.", None

    _reset_attempts()
    user_dict = {
        "id":           user.id,
        "username":     user.username,
        "email":        user.email,
        "avatar_emoji": user.avatar_emoji,
    }
    return True, "Logged in successfully!", user_dict


# ── Session validation (Fix #11) ──────────────────────────────────────
def validate_session(db: Session) -> bool:
    """
    Verify the logged-in user still exists and is active in the DB.
    Call this at app startup to prevent stale sessions.
    """
    user = st.session_state.get("user")
    if not user:
        return False
    db_user = db.query(User).filter(
        User.id == user["id"],
        User.is_active == True
    ).first()
    if not db_user:
        st.session_state.user = None
        st.session_state.room = None
        return False
    return True
