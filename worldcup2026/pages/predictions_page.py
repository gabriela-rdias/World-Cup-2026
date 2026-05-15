"""
pages/predictions_page.py
-------------------------
Phase-based prediction hub.
Tabs: Group Stage (sub-tabs A–L) | R32 | R16 | QF | SF | Final | Tournament Winner
Each group sub-tab shows match predictions AND group standings predictions together.
Knockout tabs are visible from day 1 but locked until teams are confirmed (not TBD).
No draw option in knockout stages.
"""
import streamlit as st
from database import get_db
from models import Team, Match, MatchStage
from utils.ui import inject_css, page_header, require_login, format_kickoff, \
    svg_icon, get_avatar_svg
from utils.deadline import is_prediction_open, prediction_deadline_label
from utils.predictions import (
    upsert_group_predictions, get_user_group_predictions,
    upsert_match_prediction, get_user_match_predictions,
    upsert_winner_prediction, get_winner_prediction,
)
from scoring import STAGE_POINTS

# ── Constants ─────────────────────────────────────────────────────────

KNOCKOUT_STAGES = [
    (MatchStage.ROUND_OF_32, "Round of 32",    2),
    (MatchStage.ROUND_OF_16, "Round of 16",    4),
    (MatchStage.QUARTER,     "Quarter-Finals",  6),
    (MatchStage.SEMI,        "Semi-Finals",     8),
    (MatchStage.FINAL,       "Final",          10),
]

COUNTRY_CODE = {
    "Brazil":"br","Argentina":"ar","France":"fr","England":"gb-eng","Germany":"de",
    "Spain":"es","Portugal":"pt","Netherlands":"nl","USA":"us","United States":"us",
    "Mexico":"mx","Canada":"ca","Japan":"jp","South Korea":"kr","Morocco":"ma",
    "Senegal":"sn","Colombia":"co","Uruguay":"uy","Ecuador":"ec","Switzerland":"ch",
    "Belgium":"be","Croatia":"hr","Serbia":"rs","Denmark":"dk","Austria":"at",
    "Poland":"pl","Australia":"au","Iran":"ir","Saudi Arabia":"sa","Cameroon":"cm",
    "Nigeria":"ng","Ghana":"gh","Ivory Coast":"ci","Venezuela":"ve","Bolivia":"bo",
    "Paraguay":"py","Qatar":"qa","Wales":"gb-wls","Tunisia":"tn","Costa Rica":"cr",
    "Algeria":"dz","Egypt":"eg","Congo DR":"cd","Uzbekistan":"uz","Peru":"pe",
    "Chile":"cl","Sweden":"se","Italy":"it","Turkey":"tr","Ukraine":"ua",
    "Scotland":"gb-sct","Hungary":"hu","Czech Republic":"cz","Czechia":"cz",
    "Mali":"ml","Burkina Faso":"bf","South Africa":"za","Iraq":"iq",
    "United Arab Emirates":"ae","Oman":"om","China PR":"cn","New Zealand":"nz",
    "Panama":"pa","Jamaica":"jm","Honduras":"hn","El Salvador":"sv",
    "Bosnia-Herzegovina":"ba","Haiti":"ht","Curaçao":"cw","Cape Verde Islands":"cv",
    "Norway":"no","Jordan":"jo","TBD": "",
}


def _flag_img(team_name: str, size: int = 24) -> str:
    clean = (team_name or "").strip()
    code  = COUNTRY_CODE.get(clean, "")
    if code:
        w = int(size * 1.35)
        return (f'<img src="https://flagcdn.com/h40/{code}.png" '
                f'style="width:{w}px;height:{size}px;object-fit:cover;'
                f'border-radius:3px;vertical-align:middle;'
                f'box-shadow:0 1px 3px rgba(0,0,0,0.3);" />')
    return "🏳️" if clean not in ("TBD", "") else "❓"


# ── Data loaders ──────────────────────────────────────────────────────

def _load_groups() -> dict[str, list[dict]]:
    with get_db() as db:
        # Auto-repair: fill missing group_letter on teams from match data
        missing = db.query(Team).filter(
            (Team.group_letter == None) | (Team.group_letter == "")
        ).first()
        if missing:
            for m in db.query(Match).filter(
                Match.group_letter != None, Match.group_letter != ""
            ).all():
                gl = (m.group_letter.strip()[-1] if m.group_letter else "")
                if not gl:
                    continue
                for tid in (m.home_team_id, m.away_team_id):
                    if tid:
                        t = db.get(Team, tid)
                        if t and not t.group_letter:
                            t.group_letter = gl
            db.commit()

        groups: dict[str, list[dict]] = {}
        for t in db.query(Team).order_by(Team.name).all():
            if t.group_letter:
                gl = t.group_letter.strip()[-1]
                groups.setdefault(gl, []).append(
                    {"id": t.id, "name": t.name, "tla": t.tla or "", "group_letter": gl}
                )
        return groups


def _load_matches_by_stage(stage: MatchStage) -> list[dict]:
    with get_db() as db:
        rows = (db.query(Match)
                  .filter(Match.stage == stage)
                  .order_by(Match.kickoff_time)
                  .all())
        result = []
        for m in rows:
            home = db.get(Team, m.home_team_id) if m.home_team_id else None
            away = db.get(Team, m.away_team_id) if m.away_team_id else None
            result.append({
                "id":           m.id,
                "stage":        m.stage,
                "status":       m.status or "SCHEDULED",
                "group_letter": m.group_letter or "",
                "kickoff_time": m.kickoff_time,
                "home_score":   m.home_score,
                "away_score":   m.away_score,
                "home_name":    home.name if home else "TBD",
                "away_name":    away.name if away else "TBD",
            })
        return result


def _load_group_matches(group_letter: str) -> list[dict]:
    return [m for m in _load_matches_by_stage(MatchStage.GROUP)
            if m["group_letter"].strip()[-1:] == group_letter]


def _load_user_match_preds(user_id, room_id) -> dict:
    with get_db() as db:
        return get_user_match_predictions(db, user_id, room_id)


def _load_winner_pred(user_id, room_id):
    with get_db() as db:
        return get_winner_prediction(db, user_id, room_id)


def _load_room_winner_picks(room_id) -> list[dict]:
    with get_db() as db:
        from models import TournamentWinnerPrediction, User as UserModel
        picks = (
            db.query(TournamentWinnerPrediction, UserModel)
              .join(UserModel, TournamentWinnerPrediction.user_id == UserModel.id)
              .filter(TournamentWinnerPrediction.room_id == room_id)
              .all()
        )
        return [
            {
                "team_id":      p.team_id,
                "username":     u.username,
                "avatar_emoji": u.avatar_emoji,
                "user_id":      u.id,
            }
            for p, u in picks
        ]


# ── Main render ───────────────────────────────────────────────────────

def render():
    inject_css()
    require_login()

    user = st.session_state.user
    room = st.session_state.get("room")

    page_header("PREDICTIONS", f"Room: {room['name']}" if room else "")

    if not room:
        st.info("Please select or join a room first.")
        if st.button("Go to Rooms →"):
            st.session_state.nav = "Rooms"
            st.rerun()
        return

    user_preds = _load_user_match_preds(user["id"], room["id"])

    tab_labels = [
        "⚽ Group Stage",
        "🔵 Round of 32",
        "🟡 Round of 16",
        "🟠 Quarter-Finals",
        "🔴 Semi-Finals",
        "🏆 Final",
        "🌟 Tournament Winner",
    ]
    tabs = st.tabs(tab_labels)

    # ── Group Stage ───────────────────────────────────────────────────
    with tabs[0]:
        _render_group_stage_tab(user, room, user_preds)

    # ── Knockout stages ───────────────────────────────────────────────
    for i, (stage, label, pts) in enumerate(KNOCKOUT_STAGES):
        with tabs[i + 1]:
            _render_knockout_tab(stage, label, pts, user, room, user_preds)

    # ── Tournament Winner ─────────────────────────────────────────────
    with tabs[6]:
        _render_winner_tab(user, room)


# ── Group Stage tab ───────────────────────────────────────────────────

def _render_group_stage_tab(user, room, user_preds):
    groups = _load_groups()
    if not groups:
        st.info("No group data yet. Go to Admin → Sync All Matches first.")
        return

    st.markdown("""
        <div style="background:var(--surface2);border:1px solid var(--border);
            border-radius:10px;padding:14px 18px;margin-bottom:18px;font-size:0.88rem;">
            Predict match results and final group standings (1st → 4th).<br>
            <span style="color:var(--secondary);font-weight:700;">3 pts</span> if all 4 correct
            &nbsp;|&nbsp;
            <span style="color:var(--secondary);font-weight:700;">1 pt</span> if 2+ correct
            &nbsp;|&nbsp;
            <span style="color:var(--text-muted);">Match results: 1 pt each</span>
        </div>
    """, unsafe_allow_html=True)

    group_keys = sorted(groups.keys())
    sub_tabs   = st.tabs([f"Group {g}" for g in group_keys])

    for sub_tab, gl in zip(sub_tabs, group_keys):
        with sub_tab:
            teams_in_group = groups[gl]
            matches        = _load_group_matches(gl)

            # ── Match predictions ─────────────────────────────────────
            if matches:
                st.markdown(
                    f"<div style='font-weight:700;font-size:0.92rem;"
                    f"color:var(--text-muted);letter-spacing:0.8px;"
                    f"margin-bottom:10px;'>MATCH PREDICTIONS</div>",
                    unsafe_allow_html=True,
                )
                for m in matches:
                    _render_match_card(m, user, room, user_preds, knockout=False)
            else:
                st.caption("No matches loaded for this group yet.")

            st.markdown("<hr style='border-color:var(--border);margin:18px 0;'>",
                        unsafe_allow_html=True)

            # ── Standings predictions ─────────────────────────────────
            st.markdown(
                "<div style='font-weight:700;font-size:0.92rem;"
                "color:var(--text-muted);letter-spacing:0.8px;"
                "margin-bottom:10px;'>GROUP STANDINGS PREDICTION</div>",
                unsafe_allow_html=True,
            )
            _render_group_standings_pred(gl, teams_in_group, user, room)


def _render_group_standings_pred(gl: str, teams: list[dict], user, room):
    with get_db() as db:
        existing = get_user_group_predictions(db, user["id"], room["id"], gl)

    team_by_id   = {t["id"]: t["name"] for t in teams}
    team_by_name = {t["name"]: t["id"] for t in teams}

    if existing:
        ordered_ids = existing + [t["id"] for t in teams if t["id"] not in existing]
    else:
        ordered_ids = [t["id"] for t in teams]

    chosen_names: list[str] = []
    selected_ids: list[int] = []

    for i in range(len(teams)):
        remaining = [team_by_id[tid] for tid in ordered_ids
                     if team_by_id.get(tid) not in chosen_names]
        if not remaining:
            break

        default_val = team_by_id.get(ordered_ids[i] if i < len(ordered_ids) else None)
        if default_val not in remaining:
            default_val = remaining[0]

        c_pos, c_flag, c_sel = st.columns([0.5, 0.5, 4])
        with c_pos:
            st.markdown(
                f"<div style='display:flex;align-items:center;height:40px;"
                f"font-weight:700;color:var(--text-muted);font-size:0.92rem;'>{i+1}.</div>",
                unsafe_allow_html=True,
            )
        with c_flag:
            st.markdown(
                f"<div style='display:flex;align-items:center;height:40px;'>"
                f"{_flag_img(default_val, 20)}</div>",
                unsafe_allow_html=True,
            )
        with c_sel:
            choice = st.selectbox(
                f"Position {i+1}",
                remaining,
                index=remaining.index(default_val),
                key=f"grp_{gl}_{i}_{room['id']}",
                label_visibility="collapsed",
            )

        chosen_names.append(choice)
        selected_ids.append(team_by_name[choice])

    st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)
    if st.button(f"Save Group {gl} Standings", key=f"save_grp_{gl}_{room['id']}",
                 use_container_width=True):
        with get_db() as db:
            ok, msg = upsert_group_predictions(db, user["id"], room["id"], gl, selected_ids)
        if ok:
            st.success(msg)
        else:
            st.error(msg)


# ── Knockout tab ──────────────────────────────────────────────────────

def _render_knockout_tab(stage: MatchStage, label: str, pts: int,
                         user, room, user_preds: dict):
    matches = _load_matches_by_stage(stage)
    all_tbd = all(
        m["home_name"] == "TBD" or m["away_name"] == "TBD"
        for m in matches
    ) if matches else True

    st.markdown(f"""
        <div style="background:var(--surface2);border:1px solid var(--border);
            border-radius:10px;padding:14px 18px;margin-bottom:18px;font-size:0.88rem;">
            {label} — each correct prediction is worth
            <span style="color:var(--secondary);font-weight:700;">{pts} pts</span>.
            No draws in knockout rounds.
        </div>
    """, unsafe_allow_html=True)

    if not matches:
        st.info("Matches for this stage haven't been scheduled yet.")
        return

    if all_tbd:
        st.markdown(f"""
            <div style="background:var(--surface2);border:1px dashed var(--border);
                border-radius:12px;padding:28px;text-align:center;margin:20px 0;">
                {svg_icon("lock", 36, "#5F6776")}
                <div style="font-size:1rem;font-weight:600;color:var(--text-muted);
                    margin-top:12px;">Teams Not Yet Confirmed</div>
                <div style="color:var(--text-dim);font-size:0.82rem;margin-top:6px;">
                    Predictions for {label} open once the qualified teams are known.
                </div>
            </div>
        """, unsafe_allow_html=True)
        return

    for m in matches:
        _render_match_card(m, user, room, user_preds, knockout=True)


# ── Match prediction card ─────────────────────────────────────────────

def _render_match_card(m: dict, user, room, user_preds: dict, knockout: bool = False):
    home_name = m.get("home_name", "TBD")
    away_name = m.get("away_name", "TBD")
    current   = user_preds.get(m["id"])
    tbd       = home_name == "TBD" or away_name == "TBD"

    open_pred, why  = is_prediction_open(m, room) if not tbd else (False, "Teams TBD")
    deadline_lbl    = prediction_deadline_label(m, room) if not tbd else ""

    if knockout:
        options_keys   = ["home", "away"]
        options_labels = [home_name.upper(), away_name.upper()]
    else:
        options_keys   = ["home", "draw", "away"]
        options_labels = [home_name.upper(), "DRAW", away_name.upper()]

    # Score / status display
    if m.get("status") == "FINISHED" and m.get("home_score") is not None:
        score_str    = f"{m['home_score']} – {m['away_score']}"
        status_txt   = "FT"
        status_color = "var(--primary)"
    elif m.get("status") in ("IN_PLAY", "PAUSED"):
        score_str    = f"{m.get('home_score',0)} – {m.get('away_score',0)}"
        status_txt   = "● LIVE"
        status_color = "#E53935"
    else:
        score_str    = "vs"
        status_txt   = format_kickoff(m.get("kickoff_time")) if m.get("kickoff_time") else ""
        status_color = "var(--text-muted)"

    # Card HTML
    your_pick_html = ""
    if current and current in options_keys:
        idx_p = options_keys.index(current)
        your_pick_html = (
            f'<div style="font-size:0.72rem;color:var(--text-muted);margin-top:6px;">'
            f'Your pick: <strong style="color:var(--secondary);">'
            f'{options_labels[idx_p]}</strong>'
            f'&nbsp;{svg_icon("check", 12, "#2E7D32")}</div>'
        )

    st.markdown(f"""
        <div style="background:var(--surface2);border:1px solid var(--border);
            border-radius:12px;padding:14px 16px;margin-bottom:10px;">
            <div style="display:flex;justify-content:space-between;
                align-items:center;margin-bottom:10px;">
                <div style="display:flex;align-items:center;gap:8px;flex:1;">
                    {_flag_img(home_name, 28)}
                    <span style="font-weight:700;font-size:0.95rem;">{home_name}</span>
                </div>
                <div style="text-align:center;padding:0 12px;">
                    <div style="font-size:1.3rem;font-weight:800;color:var(--text);">
                        {score_str}
                    </div>
                    <div style="color:{status_color};font-size:0.68rem;font-weight:700;">
                        {status_txt}
                    </div>
                </div>
                <div style="display:flex;align-items:center;justify-content:flex-end;
                    gap:8px;flex:1;">
                    <span style="font-weight:700;font-size:0.95rem;">{away_name}</span>
                    {_flag_img(away_name, 28)}
                </div>
            </div>
            {f'<div style="text-align:center;color:var(--text-dim);font-size:0.7rem;">{deadline_lbl}</div>' if deadline_lbl else ""}
            {your_pick_html}
        </div>
    """, unsafe_allow_html=True)

    if tbd:
        st.markdown(
            '<div style="text-align:center;padding:8px;background:var(--surface3);'
            'border-radius:8px;font-size:0.82rem;color:var(--text-dim);margin-bottom:16px;">'
            f'{svg_icon("lock",13,"#5F6776")} Waiting for teams to be confirmed</div>',
            unsafe_allow_html=True,
        )
        return

    if m.get("status") == "FINISHED":
        st.markdown("<div style='margin-bottom:14px;'></div>", unsafe_allow_html=True)
        return

    if open_pred:
        safe_idx = options_keys.index(current) if current in options_keys else 0
        choice = st.radio(
            "Pick",
            options_keys,
            index=safe_idx,
            format_func=lambda x: options_labels[options_keys.index(x)],
            horizontal=True,
            label_visibility="collapsed",
            key=f"pred_{m['id']}_{room['id']}",
        )
        col_save, _ = st.columns([1, 3])
        with col_save:
            if st.button("Save", key=f"save_{m['id']}_{room['id']}",
                         use_container_width=True):
                with get_db() as db:
                    ok, msg = upsert_match_prediction(
                        db, user["id"], m["id"], room["id"], choice
                    )
                if ok:
                    st.toast(f"Saved: {options_labels[options_keys.index(choice)]}", icon="✅")
                    st.rerun()
                else:
                    st.error(msg)
    else:
        pick_part = ""
        if current and current in options_keys:
            pick_part = (
                f' &nbsp;·&nbsp; Your pick: '
                f'<b style="color:var(--secondary);">'
                f'{options_labels[options_keys.index(current)]}</b>'
            )
        st.markdown(
            f'<div style="text-align:center;padding:8px;background:var(--surface3);'
            f'border-radius:8px;font-size:0.82rem;color:var(--text-muted);margin-bottom:16px;">'
            f'{svg_icon("lock",13,"#B8960C")} {why}{pick_part}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-bottom:6px;'></div>", unsafe_allow_html=True)


# ── Tournament Winner tab ─────────────────────────────────────────────

def _render_winner_tab(user, room):
    with get_db() as db:
        teams      = db.query(Team).order_by(Team.name).all()
        options    = {t.name: t.id for t in teams}
        current_id = get_winner_prediction(db, user["id"], room["id"])

    picks    = _load_room_winner_picks(room["id"])
    cur_name = next((name for name, tid in options.items() if tid == current_id), None)

    if cur_name:
        winner_content = (
            f'<div style="font-size:2.5rem;margin:10px 0;">{_flag_img(cur_name, 56)}</div>'
            f'<div style="font-weight:700;font-size:1.15rem;">{cur_name}</div>'
        )
    else:
        winner_content = '<p style="color:var(--text-dim);">Make your pick below</p>'

    st.markdown(f"""
        <div style="background:var(--surface2);border:2px solid var(--secondary);
            border-radius:15px;padding:24px;text-align:center;margin-bottom:22px;">
            <div style="font-weight:800;font-size:1.05rem;margin-bottom:4px;">
                World Cup Winner Prediction
            </div>
            <div style="color:var(--secondary);font-weight:800;font-size:1.1rem;margin-bottom:8px;">
                Worth 15 Points
            </div>
            {winner_content}
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col1:
        selected = st.selectbox(
            "Select Champion",
            list(options.keys()),
            index=list(options.keys()).index(cur_name) if cur_name in options else 0,
            label_visibility="collapsed",
        )
    with col2:
        if st.button("Save", key="save_winner_btn", use_container_width=True):
            with get_db() as db:
                ok, msg = upsert_winner_prediction(
                    db, user["id"], room["id"], options[selected]
                )
            if ok:
                st.toast("Winner prediction saved!", icon="🏆")
                st.rerun()
            else:
                st.error(msg)

    if picks:
        st.markdown("---")
        st.markdown("**What others picked**")
        cols = st.columns(4)
        for i, pick in enumerate(picks):
            with cols[i % 4]:
                team_name = next(
                    (n for n, tid in options.items() if tid == pick["team_id"]), "TBD"
                )
                st.markdown(f"""
                    <div style="background:var(--surface2);border:1px solid var(--border);
                        border-radius:10px;padding:10px;text-align:center;margin-bottom:8px;">
                        {get_avatar_svg(pick['avatar_emoji'], 24)}
                        <div style="font-size:0.75rem;font-weight:600;margin-top:4px;
                            overflow:hidden;text-overflow:ellipsis;
                            white-space:nowrap;">{pick['username']}</div>
                        <div style="margin:5px 0;">{_flag_img(team_name, 20)}</div>
                        <div style="font-size:0.78rem;color:var(--text-muted);">{team_name}</div>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No winner predictions in this room yet.")
