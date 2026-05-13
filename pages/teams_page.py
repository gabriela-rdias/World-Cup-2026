"""
pages/teams_page.py - Teams browser with country flag images and SVG form dots.
"""
import streamlit as st
from database import get_db
from models import Team, Match, MatchStage
from api.football_api import get_team_recent_matches, _fallback_teams
from utils.ui import inject_css, page_header, require_login, flag_emoji
from utils.standings import get_full_group_table
from utils.svg_icons import icon as _icon

# Map team TLA/name to ISO2 country code for flagcdn.com
COUNTRY_CODE = {
    "Brazil":"br","Argentina":"ar","France":"fr","England":"gb-eng","Germany":"de",
    "Spain":"es","Portugal":"pt","Netherlands":"nl","USA":"us","Mexico":"mx",
    "Canada":"ca","Japan":"jp","South Korea":"kr","Morocco":"ma","Senegal":"sn",
    "Colombia":"co","Uruguay":"uy","Ecuador":"ec","Switzerland":"ch","Belgium":"be",
    "Croatia":"hr","Serbia":"rs","Denmark":"dk","Austria":"at","Poland":"pl",
    "Australia":"au","Iran":"ir","Saudi Arabia":"sa","Cameroon":"cm","Nigeria":"ng",
    "Ghana":"gh","Ivory Coast":"ci","Venezuela":"ve","Bolivia":"bo","Paraguay":"py",
    "Qatar":"qa","Wales":"gb-wls","Tunisia":"tn","Costa Rica":"cr",
    # WC2022 extras
    "Algeria":"dz","Egypt":"eg","Cameroon":"cm",
}

def _flag_img(team_name: str, size: int = 24) -> str:
    code = COUNTRY_CODE.get(team_name, "")
    if code:
        return f'<img src="https://flagcdn.com/h{size}/{code}.png" height="{size}" style="border-radius:2px;vertical-align:middle;" />'
    return f'<span style="font-size:{size}px;">{flag_emoji(team_name)}</span>'

def _dot(result: str) -> str:
    m = {"win":"dot-win","draw":"dot-draw","loss":"dot-loss","none":"dot-none",None:"dot-none"}
    return _icon(m.get(result,"dot-none"), 10)

def _load_teams() -> list[dict]:
    with get_db() as db:
        teams = db.query(Team).order_by(Team.name).all()
        return [{"id":t.id,"name":t.name,"short_name":t.short_name or "",
                 "tla":t.tla or "","group_letter":t.group_letter or "","crest_url":t.crest_url or ""}
                for t in teams]

def _load_group_table(group_letter: str) -> list[dict]:
    with get_db() as db:
        return get_full_group_table(db, group_letter)

def _load_recent_matches(team_id: int) -> list[dict]:
    with get_db() as db:
        return get_team_recent_matches(db, team_id, limit=5)


def render():
    inject_css()
    require_login()
    page_header("TEAMS", "All FIFA World Cup nations")

    teams = _load_teams()
    if not teams:
        raw = _fallback_teams()
        st.info("Team data not yet synced. Showing static list. Load data in Admin.")
        _render_static_teams(raw)
        return

    col_search, col_group = st.columns([3, 1])
    with col_search:
        search = st.text_input("Search team", placeholder="e.g. Brazil, Spain…")
    with col_group:
        groups = sorted({t["group_letter"] for t in teams if t["group_letter"]})
        group_filter = st.selectbox("Group", options=["All"] + groups)

    filtered = teams
    if search:
        filtered = [t for t in filtered if search.lower() in t["name"].lower()]
    if group_filter != "All":
        filtered = [t for t in filtered if t["group_letter"] == group_filter]

    st.markdown(f"<p style='color:#C4A4A4;'>{len(filtered)} team(s) found</p>", unsafe_allow_html=True)

    cols = st.columns(3)
    for idx, team in enumerate(filtered):
        with cols[idx % 3]:
            _render_team_card(team)


def _render_team_card(team: dict):
    flag_html  = _flag_img(team["name"], 32)
    group_txt  = f"Group {team['group_letter']}" if team["group_letter"] else "Group TBD"
    recent     = _load_recent_matches(team["id"])
    form_dots  = _build_form_dots(recent, team["id"])

    with st.expander(f"{team['name']}  ·  {group_txt}"):
        st.markdown(
            f"""
            <div style="background:#2C1010;border:1px solid #5C2020;border-radius:10px;padding:14px;
                text-align:center;margin-bottom:12px;">
                <div style="font-size:2rem;">{flag_html}</div>
                <div style="font-weight:700;font-size:1rem;margin:6px 0 2px 0;">{team['name']}</div>
                <div style="color:#C4A4A4;font-size:0.78rem;">{group_txt}</div>
                <div style="margin-top:8px;">{form_dots}</div>
                <div style="color:#C4A4A4;font-size:0.7rem;margin-top:3px;">Recent form (last 5)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if team["group_letter"]:
            table = _load_group_table(team["group_letter"])
            if table:
                st.markdown("**Group Standing**")
                for row in table:
                    is_this = row["team_id"] == team["id"]
                    bg      = "#CC0000" if is_this else "rgba(0,0,0,0.15)"
                    row_flag = _flag_img(row["team_name"], 16)
                    st.markdown(
                        f"""<div style="background:{bg};border-radius:6px;
                            padding:5px 10px;margin-bottom:3px;
                            display:flex;align-items:center;justify-content:space-between;
                            font-size:0.78rem;">
                            <span style="display:flex;align-items:center;gap:6px;">
                                <span>{row['position']}.</span>
                                {row_flag}
                                <span style="color:#F5F0F0;">{row['team_name']}</span>
                            </span>
                            <span style="color:#D4AF37;font-weight:700;">{row['pts']} pts</span>
                        </div>""",
                        unsafe_allow_html=True,
                    )

        if recent:
            st.markdown("**Recent Matches**")
            for m in reversed(recent[-5:]):
                ht  = m.get("home_team", {})
                at  = m.get("away_team", {})
                hs  = m.get("home_score")
                as_ = m.get("away_score")
                if hs is not None and as_ is not None:
                    t_is_home = ht.get("id") == team["id"]
                    if hs == as_:   result = "draw"
                    elif (t_is_home and hs > as_) or (not t_is_home and as_ > hs): result = "win"
                    else:           result = "loss"
                    score_str = f"{hs}–{as_}"
                else:
                    result    = "none"
                    score_str = "–"
                opp      = at if ht.get("id") == team["id"] else ht
                opp_name = opp.get("shortName", opp.get("name", "?"))
                opp_flag = _flag_img(opp.get("name", ""), 16)
                dot      = _dot(result)
                st.markdown(
                    f"""<div style="font-size:0.78rem;padding:3px 0;color:#C4A4A4;
                        display:flex;align-items:center;gap:6px;">
                        {dot} <span>vs</span> {opp_flag}
                        <span>{opp_name}</span>
                        <span style="color:#F5F0F0;font-weight:600;margin-left:4px;">{score_str}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No recent match data available.")


def _build_form_dots(recent: list[dict], team_id: int) -> str:
    dots = []
    for m in recent[-5:]:
        hs  = m.get("home_score")
        as_ = m.get("away_score")
        ht  = m.get("home_team", {})
        if hs is None or as_ is None:
            dots.append(_dot(None))
            continue
        t_is_home = ht.get("id") == team_id
        if hs == as_:
            dots.append(_dot("draw"))
        elif (t_is_home and hs > as_) or (not t_is_home and as_ > hs):
            dots.append(_dot("win"))
        else:
            dots.append(_dot("loss"))
    if not dots:
        dots = [_dot(None)] * 5
    return " ".join(dots)


def _render_static_teams(raw: list[dict]):
    cols = st.columns(4)
    for idx, t in enumerate(raw):
        with cols[idx % 4]:
            flag_html = _flag_img(t["name"], 40)
            st.markdown(
                f"""<div style="background:rgba(0,0,0,0.2);border:1px solid rgba(255,255,255,0.1);
                    border-radius:10px;padding:12px;text-align:center;margin-bottom:8px;">
                    <div style="margin-bottom:6px;">{flag_html}</div>
                    <div style="font-size:0.85rem;font-weight:600;color:#FFFFFF;">{t['name']}</div>
                    <div style="color:#C4A4A4;font-size:0.72rem;">{t['tla']}</div>
                </div>""",
                unsafe_allow_html=True,
            )
