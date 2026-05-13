from utils.svg_icons import icon as _svg_icon
"""
pages/matches_page.py - All matches. All DB access inside session blocks.
"""
import streamlit as st
from datetime import datetime
from database import get_db
from models import Match, Team, MatchStage
from utils.ui import inject_css, page_header, require_login, format_kickoff, match_result_badge, stage_badge, flag_emoji
from utils.predictions import upsert_match_prediction, get_user_match_predictions, get_match_predictions_by_room
from scoring import STAGE_POINTS

STAGE_LABELS = {
    MatchStage.GROUP:       "Group Stage",
    MatchStage.ROUND_OF_32: "Round of 32",
    MatchStage.ROUND_OF_16: "Round of 16",
    MatchStage.QUARTER:     "Quarter-Final",
    MatchStage.SEMI:        "Semi-Final",
    MatchStage.FINAL:       "Final",
}


def _load_all_matches() -> list[dict]:
    with get_db() as db:
        matches = db.query(Match).order_by(Match.kickoff_time).all()
        result  = []
        for m in matches:
            home = db.get(Team, m.home_team_id) if m.home_team_id else None
            away = db.get(Team, m.away_team_id) if m.away_team_id else None
            result.append({
                "id":           m.id,
                "stage":        m.stage,
                "group_letter": m.group_letter or "",
                "matchday":     m.matchday or 0,
                "status":       m.status or "SCHEDULED",
                "kickoff_time": m.kickoff_time,
                "venue":        m.venue or "",
                "home_score":   m.home_score,
                "away_score":   m.away_score,
                "result":       m.result,
                "home_id":      home.id   if home else None,
                "home_name":    home.name if home else "TBD",
                "away_id":      away.id   if away else None,
                "away_name":    away.name if away else "TBD",
            })
        return result


def _load_team_names() -> list[str]:
    with get_db() as db:
        teams = db.query(Team).order_by(Team.name).all()
        return [t.name for t in teams]


def _load_user_preds(user_id, room_id) -> dict:
    with get_db() as db:
        return get_user_match_predictions(db, user_id, room_id)


def _load_friends_preds(match_id, room_id) -> list[dict]:
    with get_db() as db:
        return get_match_predictions_by_room(db, match_id, room_id)


def render():
    inject_css()
    require_login()

    user = st.session_state.user
    room = st.session_state.get("room")

    page_header("MATCHES", "All FIFA World Cup 2026 fixtures")

    all_matches = _load_all_matches()

    if not all_matches:
        st.info("No match data yet. Go to Admin → Demo Data to load fixtures.")
        return

    user_preds = _load_user_preds(user["id"], room["id"]) if room else {}

    # ── Filters ──────────────────────────────
    with st.expander("Filter Matches", expanded=False):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            stage_filter = st.selectbox("Stage", ["All"] + list(STAGE_LABELS.values()))
        with fc2:
            team_names   = _load_team_names()
            team_filter  = st.selectbox("Team", ["All"] + team_names)
        with fc3:
            status_filter = st.selectbox("Status", ["All", "Upcoming", "Finished", "Live"])

    filtered = all_matches
    if stage_filter != "All":
        sk = {v: k for k, v in STAGE_LABELS.items()}.get(stage_filter)
        if sk:
            filtered = [m for m in filtered if m["stage"] == sk]
    if team_filter != "All":
        filtered = [m for m in filtered if team_filter in (m["home_name"], m["away_name"])]
    if status_filter == "Upcoming":
        filtered = [m for m in filtered if m["status"] == "SCHEDULED"]
    elif status_filter == "Finished":
        filtered = [m for m in filtered if m["status"] == "FINISHED"]
    elif status_filter == "Live":
        filtered = [m for m in filtered if m["status"] in ("IN_PLAY", "PAUSED")]

    st.markdown(f"<p style='color:#9A9A9A;'>Showing {len(filtered)} matches</p>",
                unsafe_allow_html=True)

    # ── Group by stage ────────────────────────
    by_stage: dict[str, list] = {}
    for m in filtered:
        by_stage.setdefault(m["stage"], []).append(m)

    for stage in list(STAGE_LABELS.keys()):
        stage_matches = by_stage.get(stage, [])
        if not stage_matches:
            continue
        pts = STAGE_POINTS.get(stage, 1)
        st.markdown(
            f"""<div style="display:flex;align-items:center;gap:12px;margin:24px 0 10px 0;">
                <h3 style="margin:0;">{STAGE_LABELS[stage]}</h3>
                <span style="background:#D4AF37;color:#141414;padding:2px 10px;
                    border-radius:4px;font-size:0.72rem;font-weight:800;">
                    {pts} PT{'S' if pts!=1 else ''}
                </span>
            </div>""",
            unsafe_allow_html=True,
        )
        for m in stage_matches:
            _render_match_row(m, user, room, user_preds)


def _render_match_row(m: dict, user: dict, room, user_preds: dict):
    home_flag    = flag_emoji(m["home_name"])
    away_flag    = flag_emoji(m["away_name"])
    current_pred = user_preds.get(m["id"])

    if m["status"] == "FINISHED" and m["home_score"] is not None:
        score_str    = f"{m['home_score']} – {m['away_score']}"
        status_label = "FT"
        status_color = "#C8102E"
    elif m["status"] in ("IN_PLAY","PAUSED"):
        score_str    = f"{m['home_score'] or 0} – {m['away_score'] or 0}"
        status_label = "LIVE"
        status_color = "#C8102E"
    else:
        score_str    = "–"
        status_label = ""
        status_color = "#9A9A9A"

    title = (f"{home_flag} {m['home_name']}  {score_str}  {m['away_name']} {away_flag}"
             + (f"  ·  {format_kickoff(m['kickoff_time'])}" if m["kickoff_time"] else ""))

    with st.expander(title, expanded=False):
        c1, c2, c3 = st.columns([2, 1, 2])
        with c1:
            st.markdown(
                f"""<div style="text-align:center;">
                    <div style="font-size:3rem;">{home_flag}</div>
                    <div style="font-size:1rem;font-weight:700;">{m['home_name']}</div>
                    <div style="color:#9A9A9A;font-size:0.78rem;">HOME</div>
                </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(
                f"""<div style="text-align:center;padding-top:10px;">
                    <div style="font-size:1.9rem;font-weight:800;">{score_str}</div>
                    <div style="color:{status_color};font-size:0.75rem;font-weight:600;">
                        {status_label}
                    </div>
                    <div style="color:#9A9A9A;font-size:0.72rem;margin-top:4px;">
                        {'Group '+m['group_letter'] if m['group_letter'] else ''}
                    </div>
                    {f'<div style="margin-top:6px;">{match_result_badge(m["result"])}</div>' if m.get("result") else ''}
                </div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(
                f"""<div style="text-align:center;">
                    <div style="font-size:3rem;">{away_flag}</div>
                    <div style="font-size:1rem;font-weight:700;">{m['away_name']}</div>
                    <div style="color:#9A9A9A;font-size:0.78rem;">AWAY</div>
                </div>""", unsafe_allow_html=True)

        st.markdown(
            f"<div style='color:#9A9A9A;font-size:0.78rem;text-align:center;margin-top:6px;'>"
            f"{format_kickoff(m['kickoff_time'])}"
            f"{'  ·  ' + m['venue'] if m['venue'] else ''}</div>",
            unsafe_allow_html=True)

        st.markdown("---")

        # Prediction widget
        if room and m["status"] != "FINISHED":
            options = {f"Home – {m['home_name']}": "home", "Draw": "draw", f"Away – {m['away_name']}": "away"}
            labels  = list(options.keys())
            rev     = {v: k for k, v in options.items()}
            idx     = labels.index(rev[current_pred]) if current_pred and current_pred in rev else 0
            pc1, pc2 = st.columns([4, 1])
            with pc1:
                choice = st.radio("Your prediction", labels, index=idx, horizontal=True,
                                  key=f"mp_{m['id']}_{room['id']}")
            with pc2:
                if st.button("Save", key=f"ms_{m['id']}_{room['id']}"):
                    with get_db() as db:
                        ok, msg = upsert_match_prediction(db, user["id"], m["id"], room["id"], options[choice])
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
        elif current_pred:
            label = {"home": f"Home – {m['home_name']}", "draw": "Draw",
                     "away": f"Away – {m['away_name']}"}.get(current_pred,"")
            st.markdown(f"<div style='color:#9A9A9A;'>Your pick: <b style='color:#F0F0F0;'>{label}</b></div>",
                        unsafe_allow_html=True)

        # Friends' predictions
        if room:
            friends = _load_friends_preds(m["id"], room["id"])
            if friends:
                st.markdown("**Friends' predictions:**")
                cols = st.columns(min(len(friends), 4))
                for i, fp in enumerate(friends):
                    pred_label = {"home": f"Home – {m['home_name']}", "draw": "Draw",
                                  "away": f"Away – {m['away_name']}"}.get(fp["predicted_result"], "")
                    correct    = _svg_icon("check",12,"#22c55e") if fp["is_scored"] and fp["points_awarded"] > 0 else \
                                 _svg_icon("x",12,"#ef4444") if fp["is_scored"] else ""
                    is_me      = fp["username"] == user["username"]
                    bg         = "#2A2A2A" if is_me else "#1E1E1E"
                    bdr        = "1px solid #C8102E" if is_me else "1px solid #3A3A3A"
                    with cols[i % 4]:
                        st.markdown(
                            f"""<div style="background:{bg};border:{bdr};border-radius:8px;
                                padding:8px;text-align:center;margin-bottom:4px;">
                                <div style="font-size:1.1rem;">{fp['avatar_emoji']}</div>
                                <div style="font-size:0.72rem;font-weight:600;">{fp['username']}</div>
                                <div style="font-size:0.72rem;color:#9A9A9A;">{pred_label}{correct}</div>
                            </div>""", unsafe_allow_html=True)
