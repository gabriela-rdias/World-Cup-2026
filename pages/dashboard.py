"""
pages/dashboard.py - Rich dashboard with completion stats (#6), social layer (#5),
room members list (#9), and validated session (#11).
"""
import streamlit as st
from datetime import datetime, date
from database import get_db
from models import Match, Team, MatchStage, RoomMember, User as UserModel
from scoring import get_leaderboard, STAGE_POINTS, get_prediction_completion, get_match_prediction_stats
from utils.ui import inject_css, page_header, require_login, format_kickoff, \
    match_result_badge, stage_badge, points_badge, flag_emoji, svg_icon
from utils.predictions import upsert_match_prediction, get_user_match_predictions, \
    get_winner_prediction, upsert_winner_prediction
from utils.deadline import is_prediction_open, prediction_deadline_label
from api.football_api import _fallback_teams

WC_START = date(2026, 6, 11)
WC_END   = date(2026, 7, 19)


# ── Data loaders ──────────────────────────────────────────────────────

def _load_todays_matches() -> list[dict]:
    now   = datetime.utcnow()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end   = now.replace(hour=23, minute=59, second=59)
    with get_db() as db:
        matches = (db.query(Match)
                     .filter(Match.kickoff_time >= start, Match.kickoff_time <= end)
                     .order_by(Match.kickoff_time).all())
        return [_match_to_dict(db, m) for m in matches]

def _load_upcoming_matches(limit=5) -> list[dict]:
    now = datetime.utcnow()
    with get_db() as db:
        matches = (db.query(Match)
                     .filter(Match.kickoff_time > now, Match.status == "SCHEDULED")
                     .order_by(Match.kickoff_time).limit(limit).all())
        return [_match_to_dict(db, m) for m in matches]

def _match_to_dict(db, m: Match) -> dict:
    home = db.get(Team, m.home_team_id) if m.home_team_id else None
    away = db.get(Team, m.away_team_id) if m.away_team_id else None
    return {
        "id": m.id, "stage": m.stage, "group_letter": m.group_letter or "",
        "status": m.status or "SCHEDULED", "kickoff_time": m.kickoff_time,
        "home_score": m.home_score, "away_score": m.away_score, "result": m.result,
        "home_name": home.name if home else "TBD",
        "away_name": away.name if away else "TBD",
    }

def _load_user_preds(user_id, room_id) -> dict:
    with get_db() as db:
        return get_user_match_predictions(db, user_id, room_id)

def _load_leaderboard(room_id) -> list[dict]:
    with get_db() as db:
        return get_leaderboard(db, room_id)

def _load_winner_pred(user_id, room_id):
    with get_db() as db:
        return get_winner_prediction(db, user_id, room_id)

def _load_completion(user_id, room_id) -> dict:
    with get_db() as db:
        return get_prediction_completion(db, user_id, room_id)

def _load_members(room_id) -> list[dict]:
    with get_db() as db:
        rows = (db.query(RoomMember, UserModel)
                  .join(UserModel, RoomMember.user_id == UserModel.id)
                  .filter(RoomMember.room_id == room_id).all())
        return [{"user_id": u.id, "username": u.username,
                 "avatar_emoji": u.avatar_emoji, "total_points": m.total_points or 0.0}
                for m, u in rows]

def _load_match_stats(match_id, room_id) -> dict:
    with get_db() as db:
        return get_match_prediction_stats(db, match_id, room_id)


# ── Main render ───────────────────────────────────────────────────────

def render():
    inject_css()
    require_login()

    user = st.session_state.user
    room = st.session_state.get("room")

    page_header("DASHBOARD", f"Welcome back, {user['username']}")

    # ── Tournament progress bar ───────────────────────────────────────
    today = date.today()
    if today < WC_START:
        days_until = (WC_START - today).days
        day_label  = f"Tournament starts in {days_until} days"
        pct        = 0.0
    elif today > WC_END:
        day_label  = "Tournament has ended"
        pct        = 1.0
    else:
        day_num   = (today - WC_START).days + 1
        total_d   = (WC_END - WC_START).days + 1
        day_label = f"Day {day_num} of {total_d}"
        pct       = day_num / total_d

    st.markdown(f"""
        <div style="background:var(--surface2);border:1px solid var(--border);
            border-radius:var(--radius);padding:18px 22px;margin-bottom:20px;">
            <div style="display:flex;justify-content:space-between;
                align-items:center;margin-bottom:10px;">
                <span style="font-weight:600;color:var(--text);">{day_label}</span>
                <span style="color:var(--text-muted);font-size:0.78rem;">
                    Jun 11 – Jul 19, 2026 · USA, Canada & Mexico
                </span>
            </div>
            <div style="background:var(--surface);border-radius:6px;
                height:8px;overflow:hidden;">
                <div style="background:linear-gradient(90deg,var(--primary),var(--secondary));
                    width:{pct*100:.1f}%;height:100%;border-radius:6px;
                    transition:width 0.6s ease;"></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if not room:
        # ── No room selected ─────────────────────────────────────────
        st.markdown(f"""
            <div style="background:var(--surface2);border:1px solid var(--border);
                border-left:3px solid var(--secondary);border-radius:var(--radius);
                padding:22px;text-align:center;margin-bottom:20px;">
                <div style="margin-bottom:12px;">{svg_icon("rooms",40,"#D4AF37")}</div>
                <div style="font-weight:700;font-size:1rem;margin-bottom:6px;
                    color:var(--text);">You're not in a room yet</div>
                <div style="color:var(--text-muted);font-size:0.88rem;">
                    Join or create a prediction room to start competing with friends.</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Go to Rooms →", use_container_width=False):
            st.session_state.nav = "Rooms"
            st.rerun()

        # Still show points guide and upcoming matches
        _render_points_guide()
        return

    # ── With room selected ────────────────────────────────────────────
    comp        = _load_completion(user["id"], room["id"])
    today_m     = _load_todays_matches()
    upcoming    = _load_upcoming_matches(5)
    user_preds  = _load_user_preds(user["id"], room["id"])
    lb          = _load_leaderboard(room["id"])
    user_entry  = next((e for e in lb if e["user_id"] == user["id"]), None)

    # ── Top stats row ─────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(_stat_card(
            svg_icon("leaderboard", 22, "#D4AF37"),
            f"#{user_entry['rank']}" if user_entry else "—",
            "Your Rank",
            f"of {len(lb)} players"
        ), unsafe_allow_html=True)
    with c2:
        pts = f"{user_entry['total_points']:.0f}" if user_entry else "0"
        st.markdown(_stat_card(
            svg_icon("trophy", 22, "#D4AF37"),
            pts,
            "Your Points",
            "total score"
        ), unsafe_allow_html=True)
    with c3:
        st.markdown(_stat_card(
            svg_icon("predictions", 22, "#B71C1C"),
            f"{comp['predicted_matches']}/{comp['total_matches']}",
            "Matches Predicted",
            f"{comp['pct']:.0f}% complete"
        ), unsafe_allow_html=True)
    with c4:
        st.markdown(_stat_card(
            svg_icon("matches", 22, "#B71C1C"),
            f"{comp['predicted_groups']}/{comp['total_groups']}",
            "Groups Predicted",
            "group standings"
        ), unsafe_allow_html=True)

    # ── Prediction completion bar (Fix #6) ───────────────────────────
    if comp["total_matches"] > 0:
        pct_pred = comp["pct"]
        bar_color = "#2E7D32" if pct_pred == 100 else "var(--primary)"
        st.markdown(f"""
            <div style="background:var(--surface2);border:1px solid var(--border);
                border-radius:var(--radius);padding:14px 18px;margin:16px 0;">
                <div style="display:flex;justify-content:space-between;
                    font-size:0.82rem;color:var(--text-muted);margin-bottom:8px;">
                    <span style="color:var(--text);font-weight:600;">
                        {svg_icon("predictions",14,"#B71C1C")} Prediction Progress
                    </span>
                    <span>{comp['predicted_matches']} of {comp['total_matches']} matches</span>
                </div>
                <div style="background:var(--surface);border-radius:6px;
                    height:10px;overflow:hidden;">
                    <div style="background:linear-gradient(90deg,{bar_color},#D4AF37);
                        width:{pct_pred:.1f}%;height:100%;border-radius:6px;"></div>
                </div>
                {"<div style='color:#2E7D32;font-size:0.75rem;margin-top:6px;font-weight:600;'>All match predictions complete!</div>" if pct_pred == 100 else f"<div style='color:var(--text-muted);font-size:0.75rem;margin-top:6px;'>{ comp['total_matches'] - comp['predicted_matches'] } matches still need your prediction</div>"}
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_main, col_side = st.columns([3, 2])

    with col_main:
        # Today's matches
        st.markdown(f'<h3 style="margin-bottom:12px;">{svg_icon("matches",18,"#B71C1C")} Today\'s Matches</h3>',
                    unsafe_allow_html=True)
        if not today_m:
            st.markdown("""
                <div style="background:var(--surface2);border:1px solid var(--border);
                    border-radius:var(--radius);padding:16px;color:var(--text-muted);
                    font-size:0.88rem;">
                    No matches today. Check the Matches page for upcoming fixtures.
                </div>
            """, unsafe_allow_html=True)
        for m in today_m:
            stats = _load_match_stats(m["id"], room["id"])
            _render_match_card(m, user, room, user_preds, stats)

        # Upcoming
        if upcoming:
            st.markdown(f'<h3 style="margin:20px 0 12px 0;">{svg_icon("clock",18,"#B71C1C")} Coming Up</h3>',
                        unsafe_allow_html=True)
            for m in upcoming[:4]:
                stats = _load_match_stats(m["id"], room["id"])
                _render_match_card(m, user, room, user_preds, stats, compact=True)

        _render_points_guide()

    with col_side:
        # ── Leaderboard preview ───────────────────────────────────────
        st.markdown(f'<h3 style="margin-bottom:12px;">{svg_icon("leaderboard",18,"#D4AF37")} {room["name"]}</h3>',
                    unsafe_allow_html=True)
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        for entry in lb[:5]:
            is_me  = entry["user_id"] == user["id"]
            bg     = "var(--surface3)" if is_me else "var(--surface2)"
            border = "1px solid var(--primary)" if is_me else "1px solid var(--border)"
            medal  = medals.get(entry["rank"], f'#{entry["rank"]}')
            st.markdown(f"""
                <div style="background:{bg};border:{border};border-radius:var(--radius-sm);
                    padding:10px 14px;margin-bottom:5px;
                    display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-size:0.88rem;display:flex;align-items:center;gap:8px;">
                        <span>{medal}</span>
                        <span style="font-size:1rem;">{entry['avatar_emoji']}</span>
                        <span style="font-weight:{'700' if is_me else '400'};color:var(--text);">
                            {entry['username']}{'&nbsp;<span style="color:var(--primary);font-size:0.7rem;">(you)</span>' if is_me else ''}
                        </span>
                    </span>
                    <span style="color:var(--secondary);font-weight:700;">
                        {entry['total_points']:.0f}
                    </span>
                </div>
            """, unsafe_allow_html=True)
        if len(lb) > 5:
            if st.button("View full leaderboard →", use_container_width=True):
                st.session_state.nav = "Leaderboard"
                st.rerun()

        # ── Room members (Fix #9) ─────────────────────────────────────
        st.markdown(f'<h3 style="margin:20px 0 10px 0;">{svg_icon("teams",18,"#B71C1C")} Members</h3>',
                    unsafe_allow_html=True)
        members = _load_members(room["id"])
        for m in members:
            is_me = m["user_id"] == user["id"]
            comp_m = ""
            st.markdown(f"""
                <div style="background:var(--surface2);border:1px solid var(--border);
                    border-radius:var(--radius-sm);padding:9px 12px;margin-bottom:4px;
                    display:flex;align-items:center;justify-content:space-between;">
                    <span style="display:flex;align-items:center;gap:8px;font-size:0.85rem;">
                        <span style="font-size:1.1rem;">{m['avatar_emoji']}</span>
                        <span style="color:{'var(--text)' if is_me else 'var(--text-muted)'};
                            font-weight:{'600' if is_me else '400'};">{m['username']}</span>
                        {' <span style="color:var(--primary);font-size:0.7rem;">(you)</span>' if is_me else ''}
                    </span>
                    <span style="color:var(--secondary);font-size:0.8rem;font-weight:600;">
                        {m['total_points']:.0f} pts
                    </span>
                </div>
            """, unsafe_allow_html=True)

        # ── Winner pick ───────────────────────────────────────────────
        st.markdown(f'<h3 style="margin:20px 0 10px 0;">{svg_icon("trophy",18,"#D4AF37")} Winner Pick</h3>',
                    unsafe_allow_html=True)
        teams      = _fallback_teams()
        team_by_id = {t["id"]: t["name"] for t in teams}
        t_options  = {t["name"]: t["id"] for t in sorted(teams, key=lambda x: x["name"])}
        cur_id     = _load_winner_pred(user["id"], room["id"])
        cur_name   = team_by_id.get(cur_id)

        if cur_name:
            st.markdown(f"""
                <div style="background:var(--surface2);border:1px solid var(--secondary);
                    border-radius:var(--radius);padding:14px;text-align:center;margin-bottom:10px;">
                    <div style="color:var(--secondary);font-size:0.68rem;font-weight:700;
                        letter-spacing:1px;">YOUR PICK</div>
                    <div style="font-size:2rem;margin:6px 0;">{flag_emoji(cur_name)}</div>
                    <div style="font-weight:700;">{cur_name}</div>
                    <div style="color:var(--text-muted);font-size:0.75rem;">Worth 15 points</div>
                </div>
            """, unsafe_allow_html=True)

        with st.expander("Change pick" if cur_name else "Pick tournament winner"):
            idx = list(t_options.keys()).index(cur_name) if cur_name in t_options else 0
            sel = st.selectbox("Winner", list(t_options.keys()), index=idx,
                               key="dash_winner_select")
            if st.button("Save Pick", key="dash_winner_save"):
                with get_db() as db:
                    ok, msg = upsert_winner_prediction(db, user["id"], room["id"], t_options[sel])
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)


# ── Helper components ─────────────────────────────────────────────────

def _stat_card(icon_html, value, label, sub):
    return f"""
        <div style="background:var(--surface2);border:1px solid var(--border);
            border-radius:var(--radius);padding:16px;text-align:center;margin-bottom:8px;">
            <div style="margin-bottom:6px;">{icon_html}</div>
            <div style="font-size:1.6rem;font-weight:800;color:var(--text);
                font-family:var(--font-display);">{value}</div>
            <div style="font-size:0.75rem;font-weight:600;color:var(--text-muted);
                margin-top:2px;">{label}</div>
            <div style="font-size:0.7rem;color:var(--text-dim);margin-top:2px;">{sub}</div>
        </div>
    """

def _render_points_guide():
    with st.expander("Points Guide"):
        items = [
            ("Group Match","1 pt"),("Round of 32","2 pts"),("Round of 16","4 pts"),
            ("Quarter-Final","6 pts"),("3rd Place","6 pts"),("Semi-Final","8 pts"),
            ("Final","10 pts"),("Group Standings","1–3 pts"),("Tournament Winner","15 pts"),
        ]
        cols = st.columns(3)
        for i, (lbl, pts) in enumerate(items):
            with cols[i % 3]:
                st.markdown(f"""
                    <div style="background:var(--surface2);border:1px solid var(--border);
                        border-radius:8px;padding:10px;text-align:center;margin-bottom:6px;">
                        <div style="color:var(--text-muted);font-size:0.72rem;">{lbl}</div>
                        <div style="color:var(--secondary);font-weight:800;
                            font-size:1.0rem;">{pts}</div>
                    </div>
                """, unsafe_allow_html=True)


def _render_match_card(m, user, room, user_preds, stats, compact=False):
    home_name    = m["home_name"]
    away_name    = m["away_name"]
    pts_worth    = STAGE_POINTS.get(m["stage"], 1)
    current_pred = user_preds.get(m["id"])

    if m["status"] == "FINISHED" and m["home_score"] is not None:
        score_str    = f"{m['home_score']} – {m['away_score']}"
        status_color = "var(--primary)"
        status_label = "FULL TIME"
    elif m["status"] in ("IN_PLAY", "PAUSED"):
        score_str    = f"{m['home_score'] or 0} – {m['away_score'] or 0}"
        status_color = "#E53935"
        status_label = "● LIVE"
    else:
        score_str    = "vs"
        status_color = "var(--text-muted)"
        status_label = format_kickoff(m["kickoff_time"])

    # Social prediction bar (Fix #5)
    total_preds  = stats.get("total", 0)
    member_label = f"{total_preds} prediction{'s' if total_preds != 1 else ''}" if total_preds else "No predictions yet"

    # Deadline check (Fix #1)
    open_pred, closed_reason = is_prediction_open(m, room) if room else (False, "No room")
    deadline_lbl = prediction_deadline_label(m, room) if room else ""

    # Prediction bar widths
    if total_preds:
        h_pct = stats.get("home", 0) / total_preds * 100
        d_pct = stats.get("draw", 0) / total_preds * 100
        a_pct = stats.get("away", 0) / total_preds * 100
    else:
        h_pct = d_pct = a_pct = 0

    pred_bar = ""
    if total_preds:
        pred_bar = f"""
        <div style="margin-top:10px;">
            <div style="display:flex;height:4px;border-radius:2px;overflow:hidden;gap:2px;">
                <div style="background:#B71C1C;width:{h_pct:.0f}%;border-radius:2px;"></div>
                <div style="background:#B8960C;width:{d_pct:.0f}%;border-radius:2px;"></div>
                <div style="background:#1565C0;width:{a_pct:.0f}%;border-radius:2px;"></div>
            </div>
            <div style="display:flex;justify-content:space-between;
                font-size:0.65rem;color:var(--text-muted);margin-top:3px;">
                <span>H {stats.get('home',0)}</span>
                <span style="color:var(--text-dim);">{member_label}</span>
                <span>A {stats.get('away',0)}</span>
            </div>
        </div>"""

    your_pick_html = ""
    if current_pred:
        pick_labels = {"home": f"H: {home_name}", "draw": "Draw", "away": f"A: {away_name}"}
        your_pick_html = f"""
        <div style="font-size:0.72rem;color:var(--text-muted);margin-top:6px;">
            Your pick: <strong style="color:var(--text);">{pick_labels.get(current_pred,'')}</strong>
            &nbsp;{svg_icon("check",12,"#2E7D32")}
        </div>"""

    st.markdown(f"""
        <div style="background:var(--surface2);border:1px solid var(--border);
            border-radius:var(--radius);padding:16px;margin-bottom:10px;
            box-shadow:var(--shadow-sm);">
            <div style="display:flex;justify-content:space-between;
                margin-bottom:10px;align-items:center;">
                <div style="display:flex;gap:6px;align-items:center;">
                    {stage_badge(m['stage'])}
                    {"<span style='color:var(--text-muted);font-size:0.72rem;'>Group " + m['group_letter'] + "</span>" if m['group_letter'] else ""}
                </div>
                <div style="color:{status_color};font-size:0.75rem;font-weight:700;">
                    {status_label}
                </div>
            </div>
            <div style="display:flex;align-items:center;justify-content:space-between;">
                <div style="text-align:center;flex:1;">
                    <div style="font-size:1.6rem;">{flag_emoji(home_name)}</div>
                    <div style="font-weight:700;font-size:0.88rem;margin-top:2px;">{home_name}</div>
                </div>
                <div style="text-align:center;padding:0 14px;">
                    <div style="font-size:1.5rem;font-weight:800;color:var(--text);">{score_str}</div>
                    <div style="color:var(--text-dim);font-size:0.68rem;margin-top:2px;">
                        {pts_worth} pt{'s' if pts_worth!=1 else ''}
                    </div>
                </div>
                <div style="text-align:center;flex:1;">
                    <div style="font-size:1.6rem;">{flag_emoji(away_name)}</div>
                    <div style="font-weight:700;font-size:0.88rem;margin-top:2px;">{away_name}</div>
                </div>
            </div>
            {f'<div style="margin-top:8px;text-align:center;">{match_result_badge(m["result"])}</div>' if m.get("result") else ""}
            {your_pick_html}
            {pred_bar}
            {f'<div style="font-size:0.68rem;color:var(--text-dim);margin-top:6px;">{svg_icon("clock",10,"#7A5050")} {deadline_lbl}</div>' if deadline_lbl and not compact else ""}
        </div>
    """, unsafe_allow_html=True)

    # Inline prediction (Fix #1 — only if open)
    if room and not compact and m["status"] not in ("FINISHED",):
        if open_pred:
            options = {f"Home – {home_name}": "home", "Draw": "draw", f"Away – {away_name}": "away"}
            labels  = list(options.keys())
            rev     = {v: k for k, v in options.items()}
            idx     = labels.index(rev[current_pred]) if current_pred and current_pred in rev else 0
            c1, c2  = st.columns([4, 1])
            with c1:
                choice = st.radio("Prediction", labels, index=idx, horizontal=True,
                                  label_visibility="collapsed",
                                  key=f"dash_pred_{m['id']}_{room['id']}")
            with c2:
                if st.button("Save", key=f"dash_save_{m['id']}_{room['id']}"):
                    with get_db() as db:
                        ok, msg = upsert_match_prediction(
                            db, user["id"], m["id"], room["id"], options[choice])
                    if ok:
                        st.toast("Prediction saved!")
                        st.rerun()
                    else:
                        st.error(msg)
        else:
            st.markdown(f"""
                <div style="font-size:0.78rem;color:var(--text-muted);padding:6px 0;
                    display:flex;align-items:center;gap:6px;">
                    {svg_icon("lock",14,"#7A5050")}
                    <span style="color:var(--text-dim);">Predictions closed — {closed_reason}</span>
                </div>
            """, unsafe_allow_html=True)
