"""
pages/predictions_page.py - Predictions hub. All DB access inside session blocks.
"""
import streamlit as st
from database import get_db
from models import Team, Match, MatchStage
from utils.ui import inject_css, page_header, require_login, require_room, flag_emoji, format_kickoff, svg_icon
from utils.deadline import is_prediction_open, prediction_deadline_label
from utils.predictions import (upsert_group_predictions, get_user_group_predictions,
                                upsert_match_prediction, get_user_match_predictions,
                                upsert_winner_prediction, get_winner_prediction)
from api.football_api import _fallback_teams
from utils.deadline import is_prediction_open, prediction_deadline_label
from scoring import STAGE_POINTS

STAGE_LABELS = {
    MatchStage.GROUP:"Group Stage", MatchStage.ROUND_OF_32:"Round of 32",
    MatchStage.ROUND_OF_16:"Round of 16", MatchStage.QUARTER:"Quarter-Finals",
    MatchStage.SEMI:"Semi-Finals", MatchStage.THIRD_PLACE:"3rd Place Play-off",
    MatchStage.FINAL:"Final",
}


def _load_groups() -> dict[str, list[dict]]:
    """Load all teams grouped by group_letter as plain dicts."""
    with get_db() as db:
        teams = db.query(Team).order_by(Team.name).all()
        groups: dict[str, list[dict]] = {}
        for t in teams:
            if t.group_letter:
                groups.setdefault(t.group_letter, []).append({
                    "id": t.id, "name": t.name,
                    "tla": t.tla or "", "group_letter": t.group_letter,
                })
        return groups


def _load_open_matches() -> list[dict]:
    with get_db() as db:
        matches = db.query(Match).filter(Match.status != "FINISHED").order_by(Match.kickoff_time).all()
        result  = []
        for m in matches:
            home = db.get(Team, m.home_team_id) if m.home_team_id else None
            away = db.get(Team, m.away_team_id) if m.away_team_id else None
            result.append({
                "id":           m.id,
                "stage":        m.stage,
                "status":       m.status or "SCHEDULED",
                "kickoff_time": m.kickoff_time,
                "home_name":    home.name if home else "TBD",
                "away_name":    away.name if away else "TBD",
            })
        return result


def _load_user_group_preds(user_id, room_id, group_letter) -> list[int]:
    with get_db() as db:
        return get_user_group_predictions(db, user_id, room_id, group_letter)


def _load_user_match_preds(user_id, room_id) -> dict:
    with get_db() as db:
        return get_user_match_predictions(db, user_id, room_id)


def _load_winner_pred(user_id, room_id):
    with get_db() as db:
        return get_winner_prediction(db, user_id, room_id)


def _load_room_winner_picks(room_id) -> list[dict]:
    with get_db() as db:
        from models import TournamentWinnerPrediction, User as UserModel
        picks = (db.query(TournamentWinnerPrediction, UserModel)
                 .join(UserModel, TournamentWinnerPrediction.user_id == UserModel.id)
                 .filter(TournamentWinnerPrediction.room_id == room_id).all())
        return [{"team_id": p.team_id, "username": u.username, "avatar_emoji": u.avatar_emoji,
                 "user_id": u.id} for p, u in picks]


def render():
    inject_css()
    require_login()
    require_room()

    user = st.session_state.user
    room = st.session_state.room

    page_header("PREDICTIONS", f"Room: {room['name']}")

    tab_groups, tab_matches, tab_winner = st.tabs([
        "Group Standings", "Match Results", "Tournament Winner"
    ])

    # ── GROUP STANDINGS ──────────────────────
    with tab_groups:
        st.markdown(
            """<div style="background:#1E1E1E;border:1px solid #3A3A3A;border-radius:10px;
                padding:14px 18px;margin-bottom:20px;">
                For each group, select the teams in your predicted finishing order (1st to 4th).<br>
                <span style="color:#D4AF37;">3 pts</span> if all 4 correct &nbsp;|&nbsp;
                <span style="color:#D4AF37;">1 pt</span> if at least 2 correct
            </div>""",
            unsafe_allow_html=True,
        )
        groups = _load_groups()
        if not groups:
            st.info("No group data yet. Load demo data in Admin first.")
        else:
            for gl in sorted(groups.keys()):
                _render_group_pred(gl, groups[gl], user, room)

    # ── MATCH RESULTS ────────────────────────
    with tab_matches:
        matches    = _load_open_matches()
        user_preds = _load_user_match_preds(user["id"], room["id"])

        if not matches:
            st.info("All matches finished or none scheduled yet.")
        else:
            total  = len(matches)
            filled = sum(1 for m in matches if m["id"] in user_preds)
            pct    = filled / total * 100 if total else 0

            st.markdown(
                f"""<div style="margin-bottom:16px;">
                    <div style="display:flex;justify-content:space-between;
                        color:#9A9A9A;font-size:0.85rem;margin-bottom:4px;">
                        <span>Predictions filled</span><span>{filled} / {total}</span>
                    </div>
                    <div style="background:#141414;border-radius:6px;height:6px;overflow:hidden;">
                        <div style="background:linear-gradient(90deg,#C8102E,#D4AF37);
                            width:{pct:.0f}%;height:100%;border-radius:6px;"></div>
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )

            by_stage: dict[str, list] = {}
            for m in matches:
                by_stage.setdefault(m["stage"], []).append(m)

            for stage in list(STAGE_LABELS.keys()):
                stage_matches = by_stage.get(stage, [])
                if not stage_matches:
                    continue
                pts = STAGE_POINTS.get(stage, 1)
                st.markdown(f"### {STAGE_LABELS[stage]} — {pts} pt{'s' if pts!=1 else ''}")
                for m in stage_matches:
                    _render_quick_pred(m, user, room, user_preds)

    # ── TOURNAMENT WINNER ────────────────────
    with tab_winner:
        st.markdown(
            """<div style="background:#1E1E1E;border:2px solid #D4AF37;border-radius:12px;
                padding:20px;margin-bottom:24px;text-align:center;">
                <div style="font-size:1.2rem;font-weight:700;margin-bottom:4px;">
                    Pick the World Cup Winner
                </div>
                <div style="color:#D4AF37;font-size:1rem;font-weight:800;">Worth 15 points</div>
                <div style="color:#9A9A9A;font-size:0.82rem;margin-top:4px;">
                    Must be set before the tournament starts.
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

        teams      = _fallback_teams()
        team_by_id = {t["id"]: t for t in teams}
        options    = {t["name"]: t["id"] for t in sorted(teams, key=lambda x: x["name"])}
        current_id = _load_winner_pred(user["id"], room["id"])
        cur_name   = team_by_id.get(current_id, {}).get("name") if current_id else None

        if cur_name:
            st.markdown(
                f"""<div style="background:#2A2A2A;border-radius:10px;padding:14px;
                    text-align:center;margin-bottom:14px;">
                    <div style="color:#9A9A9A;font-size:0.75rem;">YOUR PICK</div>
                    <div style="font-size:2.5rem;">{flag_emoji(cur_name)}</div>
                    <div style="font-size:1.1rem;font-weight:700;">{cur_name}</div>
                </div>""",
                unsafe_allow_html=True,
            )

        idx      = list(options.keys()).index(cur_name) if cur_name in options else 0
        selected = st.selectbox("Select your winner", list(options.keys()), index=idx)

        if st.button("Save Winner Prediction", use_container_width=True):
            with get_db() as db:
                ok, msg = upsert_winner_prediction(db, user["id"], room["id"], options[selected])
            st.success(msg) if ok else st.error(msg)
            if ok:
                st.rerun()

        # Room's picks
        st.markdown("---")
        st.subheader("What your room picked")
        picks = _load_room_winner_picks(room["id"])
        if picks:
            cols = st.columns(min(len(picks), 4))
            for i, pick in enumerate(picks):
                t_info = team_by_id.get(pick["team_id"], {})
                t_name = t_info.get("name", "Unknown")
                is_me  = pick["user_id"] == user["id"]
                bg     = "#2A2A2A" if is_me else "#1E1E1E"
                bdr    = "1px solid #C8102E" if is_me else "1px solid #3A3A3A"
                with cols[i % 4]:
                    st.markdown(
                        f"""<div style="background:{bg};border:{bdr};border-radius:10px;
                            padding:12px;text-align:center;margin-bottom:8px;">
                            <div style="font-size:1.4rem;">{pick['avatar_emoji']}</div>
                            <div style="font-size:0.78rem;font-weight:600;">{pick['username']}</div>
                            <div style="font-size:1.4rem;margin:4px 0;">{flag_emoji(t_name)}</div>
                            <div style="font-size:0.78rem;color:#F0F0F0;">{t_name}</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )
        else:
            st.info("No winner predictions in this room yet.")


def _render_group_pred(gl: str, teams: list[dict], user: dict, room: dict):
    existing = _load_user_group_preds(user["id"], room["id"], gl)
    team_by_id   = {t["id"]: t["name"] for t in teams}
    team_by_name = {t["name"]: t["id"] for t in teams}

    # Build default order
    if existing:
        ordered_ids = existing + [t["id"] for t in teams if t["id"] not in existing]
    else:
        ordered_ids = [t["id"] for t in teams]

    with st.expander(f"Group {gl}  ·  {len(teams)} teams", expanded=False):
        st.caption("Select the teams in your predicted finishing order.")
        selected_ids = []
        chosen_names = []

        for pos_idx, pos_label in enumerate(["1st", "2nd", "3rd", "4th"][:len(teams)]):
            remaining = [team_by_id[tid] for tid in ordered_ids
                         if team_by_id.get(tid) and team_by_id[tid] not in chosen_names]
            if not remaining:
                break
            default_name = team_by_id.get(ordered_ids[pos_idx], remaining[0])
            if default_name not in remaining:
                default_name = remaining[0]
            choice = st.selectbox(pos_label, remaining,
                                  index=remaining.index(default_name),
                                  key=f"grp_{gl}_{pos_idx}_{room['id']}")
            chosen_names.append(choice)
            selected_ids.append(team_by_name.get(choice))

        if st.button(f"Save Group {gl}", key=f"save_grp_{gl}_{room['id']}"):
            valid = [i for i in selected_ids if i is not None]
            if len(valid) == len(teams):
                with get_db() as db:
                    ok, msg = upsert_group_predictions(db, user["id"], room["id"], gl, valid)
                st.success(msg) if ok else st.error(msg)
            else:
                st.error("Please select all positions.")


def _render_quick_pred(m: dict, user: dict, room: dict, user_preds: dict):
    current         = user_preds.get(m["id"])
    open_pred, why  = is_prediction_open(m, room)
    deadline_lbl    = prediction_deadline_label(m, room)
    options = {f"Home – {m['home_name']}": "home", "Draw": "draw",
               f"Away – {m['away_name']}": "away"}
    labels  = list(options.keys())
    rev     = {v: k for k, v in options.items()}
    idx     = labels.index(rev[current]) if current and current in rev else 0

    c1, c2, c3 = st.columns([3, 2, 1])
    with c1:
        pred_badge = ""
        if current:
            pred_badge = f" <span style=\"background:var(--surface3);color:var(--secondary);padding:1px 7px;border-radius:20px;font-size:0.65rem;\">{rev.get(current,'')}</span>"
        locked_icon = svg_icon("lock",12,"#B8960C") if not open_pred else ""
        st.markdown(
            f"<div style=\"padding:8px 0;font-size:0.88rem;\">"
            f"{locked_icon} {flag_emoji(m['home_name'])} <b>{m['home_name']}</b> vs "
            f"{flag_emoji(m['away_name'])} <b>{m['away_name']}</b>{pred_badge}"
            f"<br><span style=\"color:var(--text-muted);font-size:0.7rem;\">"
            f"{format_kickoff(m['kickoff_time'])} &nbsp;·&nbsp; {deadline_lbl}</span></div>",
            unsafe_allow_html=True,
        )
    with c2:
        if open_pred:
            choice = st.radio("pred", labels, index=idx, horizontal=True,
                              label_visibility="collapsed",
                              key=f"qp_{m['id']}_{room['id']}")
        else:
            st.markdown(f"<span style=\"color:var(--text-muted);font-size:0.78rem;\">{why}</span>",
                        unsafe_allow_html=True)
            choice = None
    with c3:
        if open_pred:
            if st.button("Save", key=f"qs_{m['id']}_{room['id']}"):
                with get_db() as db:
                    ok, msg = upsert_match_prediction(db, user["id"], m["id"], room["id"], options[choice])
                if ok:
                    st.toast("Saved!")
                    st.rerun()
                else:
                    st.error(msg)
