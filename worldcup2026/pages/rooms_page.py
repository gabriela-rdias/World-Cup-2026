"""
pages/rooms_page.py
-------------------
Room management — create, join, view and manage prediction rooms.
All database objects are converted to plain dicts before the session
closes, so nothing can cause a DetachedInstanceError.
"""

import streamlit as st
from database import get_db
from models import DeadlineType, User, Room
from utils.rooms import create_room, join_room, get_user_rooms
from utils.ui import inject_css, page_header, require_login, get_avatar_svg
from scoring import get_leaderboard

DEADLINE_OPTIONS = {
    "1 hour before kickoff":          DeadlineType.HOUR_BEFORE,
    "Day before the match":           DeadlineType.DAY_BEFORE,
    "Fixed window after matchup set": DeadlineType.FIXED_WINDOW,
}


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _room_to_dict(r) -> dict:
    """Safely convert any Room ORM object to a plain dict."""
    return {
        "id":                  r.id,
        "name":                r.name,
        "invite_code":         r.invite_code,
        "owner_id":            r.owner_id,
        "deadline_type":       r.deadline_type,
        "fixed_window_hours":  r.fixed_window_hours or 24,
        "description":         r.description or "",
    }


def _load_my_rooms(user_id: int) -> list[dict]:
    """Load all rooms for a user as plain dicts (session opens and closes here)."""
    with get_db() as db:
        rooms_orm = get_user_rooms(db, user_id)
        return [_room_to_dict(r) for r in rooms_orm]


def _load_leaderboard(room_id: int) -> list[dict]:
    """Load leaderboard for a room (session opens and closes here)."""
    with get_db() as db:
        return get_leaderboard(db, room_id)


# ─────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────

def render():
    inject_css()
    require_login()

    user        = st.session_state.user
    active_room = st.session_state.get("room")

    page_header("ROOMS", "Create or join a prediction room")

    tab_my, tab_create, tab_join = st.tabs(["My Rooms", "Create Room", "Join Room"])

    # ════════════════════════════════════════
    # MY ROOMS
    # ════════════════════════════════════════
    with tab_my:
        my_rooms = _load_my_rooms(user["id"])

        if not my_rooms:
            st.info("You haven't joined any rooms yet. Create one or use an invite code!")
        else:
            for room_dict in my_rooms:
                _render_room_card(room_dict, user, active_room)

    # ════════════════════════════════════════
    # CREATE ROOM
    # ════════════════════════════════════════
    with tab_create:
        st.markdown("<br>", unsafe_allow_html=True)

        with st.form("create_room_form"):
            room_name   = st.text_input("Room Name", placeholder="e.g. Nova SBE 2026")
            description = st.text_area("Description (optional)",
                                       placeholder="A quick description for your friends…",
                                       height=80)
            st.markdown("**Prediction Deadline**")
            st.caption("When do predictions close for each match?")
            deadline_label = st.selectbox("Deadline type",
                                          options=list(DEADLINE_OPTIONS.keys()))
            deadline_type  = DEADLINE_OPTIONS[deadline_label]

            fixed_hours = 24
            if deadline_type == DeadlineType.FIXED_WINDOW:
                fixed_hours = st.number_input("Hours after matchup is announced",
                                              min_value=1, max_value=168,
                                              value=24, step=1)

            submitted = st.form_submit_button("Create Room", use_container_width=True)

        if submitted:
            with get_db() as db:
                db_user = db.get(User, user["id"])
                ok, msg, new_room = create_room(
                    db, room_name, db_user,
                    description=description,
                    deadline_type=deadline_type,
                    fixed_window_hours=int(fixed_hours),
                )

            if ok:
                # Set room as active and go straight to Dashboard
                st.session_state.room = new_room
                st.session_state.nav  = "Dashboard"
                st.rerun()
            else:
                st.error(msg)

    # ════════════════════════════════════════
    # JOIN ROOM
    # ════════════════════════════════════════
    with tab_join:
        st.markdown("<br>", unsafe_allow_html=True)

        with st.form("join_room_form"):
            invite_code = st.text_input(
                "Invite Code",
                placeholder="e.g. AB12CD34",
                help="Ask your friend for the 8-character room code",
            )
            submitted = st.form_submit_button("Join Room", use_container_width=True)

        if submitted:
            with get_db() as db:
                db_user = db.get(User, user["id"])
                ok, msg, joined_room = join_room(db, invite_code, db_user)

            if ok:
                # joined_room is already a dict (returned by our fixed join_room)
                st.success(msg)
                st.session_state.room = joined_room
                st.rerun()
            else:
                st.error(msg)


# ─────────────────────────────────────────────
# ROOM CARD
# ─────────────────────────────────────────────

def _render_room_card(room: dict, user: dict, active_room):
    """
    Render a single room card.
    `room` is a plain dict — no ORM object is used here.
    """
    is_active = bool(active_room and active_room.get("id") == room["id"])
    is_owner  = room["owner_id"] == user["id"]

    deadline_labels = {
        DeadlineType.HOUR_BEFORE:  "Closes 1 hour before kickoff",
        DeadlineType.DAY_BEFORE:   "Closes the day before the match",
        DeadlineType.FIXED_WINDOW: f"Fixed window ({room['fixed_window_hours']}h after announced)",
    }
    deadline_txt = deadline_labels.get(room["deadline_type"], "Unknown deadline")

    active_marker = "  ·  ACTIVE" if is_active else ""
    owner_marker  = "  ·  Owner" if is_owner else ""

    border_color = "var(--primary)" if is_active else "var(--border)"

    with st.expander(
        f"{room['name']}{active_marker}{owner_marker}  ·  Code: {room['invite_code']}",
        expanded=is_active,
    ):
        col_info, col_action = st.columns([3, 1])

        with col_info:
            if room["description"]:
                st.markdown(
                    f"<p style='color:var(--text-muted);font-size:0.9rem;'>{room['description']}</p>",
                    unsafe_allow_html=True,
                )

            # Invite code display
            st.markdown(
                f"""
                <div style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:10px 16px;display:inline-block;margin-bottom:10px;">
                    <span style="color:var(--text-muted);font-size:0.72rem;letter-spacing:1px;">
                        INVITE CODE &nbsp;&nbsp;
                    </span>
                    <span style="color:var(--secondary);font-weight:800;font-size:1.1rem;letter-spacing:5px;">
                        {room['invite_code']}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                f"<div style='color:var(--text-muted);font-size:0.8rem;'>⏱ {deadline_txt}</div>",
                unsafe_allow_html=True,
            )

        with col_action:
            if not is_active:
                if st.button("Switch to room", key=f"switch_{room['id']}",
                             use_container_width=True):
                    st.session_state.room = room
                    st.rerun()
            else:
                st.success("Active")

        # ── Leaderboard ───────────────────────
        st.markdown("**Members**")
        lb = _load_leaderboard(room["id"])

        if lb:
            medals = {1: "1st", 2: "2nd", 3: "3rd"}
            for entry in lb:
                rank_label = medals.get(entry["rank"], f"#{entry['rank']}")
                is_me      = entry["user_id"] == user["id"]
                bg         = "#2A2A2A" if is_me else "#1E1E1E"
                border     = "1px solid #C8102E" if is_me else "1px solid #3A3A3A"
                me_label   = " (you)" if is_me else ""

                st.markdown(
                    f"""
                    <div style="background:{bg};border:{border};border-radius:8px;
                        padding:8px 14px;margin-bottom:4px;
                        display:flex;justify-content:space-between;align-items:center;">
                        <span style="font-size:0.88rem;">
                            {rank_label} &nbsp; <span style="display:inline-flex;vertical-align:middle;">{get_avatar_svg(entry['avatar_emoji'], 22)}</span> &nbsp;
                            <b>{entry['username']}</b>
                            <span style="color:var(--primary);font-size:0.75rem;">{me_label}</span>
                        </span>
                        <span style="color:var(--secondary);font-weight:700;">
                            {entry['total_points']:.0f} pts
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No scored predictions yet.")

        # ── Owner settings ────────────────────
        if is_owner:
            st.markdown("---")
            st.markdown("**Room Settings** — owner only")

            current_deadline_label = next(
                (k for k, v in DEADLINE_OPTIONS.items() if v == room["deadline_type"]),
                list(DEADLINE_OPTIONS.keys())[0],
            )

            with st.form(f"settings_{room['id']}"):
                new_deadline_label = st.selectbox(
                    "Prediction deadline",
                    options=list(DEADLINE_OPTIONS.keys()),
                    index=list(DEADLINE_OPTIONS.keys()).index(current_deadline_label),
                    key=f"dl_{room['id']}",
                )
                new_fixed_hours = room["fixed_window_hours"]
                if DEADLINE_OPTIONS[new_deadline_label] == DeadlineType.FIXED_WINDOW:
                    new_fixed_hours = st.number_input(
                        "Hours after matchup announced",
                        min_value=1, max_value=168,
                        value=new_fixed_hours,
                        key=f"fh_{room['id']}",
                    )
                save = st.form_submit_button("Save Settings")

            if save:
                with get_db() as db:
                    db_room = db.get(Room, room["id"])
                    if db_room:
                        db_room.deadline_type      = DEADLINE_OPTIONS[new_deadline_label]
                        db_room.fixed_window_hours = int(new_fixed_hours)
                st.success("Settings saved!")
                st.rerun()
