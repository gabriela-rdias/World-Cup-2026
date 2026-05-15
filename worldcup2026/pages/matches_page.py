"""
pages/matches_page.py - Official Match Calendar & Group Standings.
"""
import streamlit as st
from datetime import datetime, date
from database import get_db
from models import Match, Team, MatchStage
from utils.ui import inject_css, page_header, require_login, format_kickoff

# ── Flag Dictionary ──────────────────────────────────────────────────
COUNTRY_CODE = {
    "Brazil":"br","Argentina":"ar","France":"fr","England":"gb-eng","Germany":"de",
    "Spain":"es","Portugal":"pt","Netherlands":"nl","USA":"us","Mexico":"mx",
    "Canada":"ca","Japan":"jp","South Korea":"kr","Morocco":"ma","Senegal":"sn",
    "Colombia":"co","Uruguay":"uy","Ecuador":"ec","Switzerland":"ch","Belgium":"be",
    "Croatia":"hr","Serbia":"rs","Denmark":"dk","Austria":"at","Poland":"pl",
    "Australia":"au","Iran":"ir","Saudi Arabia":"sa","Cameroon":"cm","Nigeria":"ng",
    "Ghana":"gh","Ivory Coast":"ci","Venezuela":"ve","Bolivia":"bo","Paraguay":"py",
    "Qatar":"qa","Wales":"gb-wls","Tunisia":"tn","Costa Rica":"cr",
    "Algeria":"dz","Egypt":"eg","Congo DR":"cd","Uzbekistan":"uz",
    "Peru":"pe", "Chile":"cl", "Sweden":"se", "Italy":"it", "Turkey":"tr",
    "Ukraine":"ua", "Scotland":"gb-sct", "Hungary":"hu", "Czech Republic":"cz",
    "Mali":"ml", "Burkina Faso":"bf", "South Africa":"za", "Iraq":"iq",
    "United Arab Emirates":"ae", "Oman":"om", "China PR":"cn", "New Zealand":"nz",
    "Panama":"pa", "Jamaica":"jm", "Honduras":"hn", "El Salvador":"sv",
    "Czechia":"cz", "Bosnia-Herzegovina":"ba", "United States":"us", "Haiti":"ht",
    "Curaçao":"cw", "Cape Verde Islands":"cv", "Norway":"no", "Jordan":"jo",
    "TBD": ""
}

def _flag_img(team_name, size=32):
    clean_name = team_name.strip() if team_name else ""
    code = COUNTRY_CODE.get(clean_name, "")
    
    if code:
        width = int(size * 1.35)
        return f"<img src='https://flagcdn.com/h40/{code}.png' style='width:{width}px; height:{size}px; object-fit:cover; border-radius:4px; vertical-align:middle; box-shadow:0 2px 5px rgba(0,0,0,0.2);' />"
    
    if clean_name == "TBD":
        return f"<span style='font-size:{size}px;line-height:1;color:var(--text-dim);'>❓</span>"
        
    return f"<span style='font-size:{size}px;line-height:1;'>🏳️</span>"

# ── Data Loading ──────────────────────────────────────────────────────
def _load_all_matches():
    with get_db() as db:
        matches = db.query(Match).filter(Match.stage != MatchStage.THIRD_PLACE).order_by(Match.kickoff_time).all()
        result  = []
        for m in matches:
            home = db.get(Team, m.home_team_id) if m.home_team_id else None
            away = db.get(Team, m.away_team_id) if m.away_team_id else None
            result.append({
                "id":           m.id,
                "stage":        m.stage,
                "group_letter": m.group_letter or "",
                "status":       m.status or "SCHEDULED",
                "kickoff_time": m.kickoff_time,
                "venue":        m.venue or "",
                "home_score":   m.home_score,
                "away_score":   m.away_score,
                "result":       m.result,
                "home_name":    home.name if home else "TBD",
                "away_name":    away.name if away else "TBD",
            })
        return result

def _load_team_names():
    with get_db() as db:
        teams = db.query(Team).order_by(Team.name).all()
        return [t.name for t in teams]

def _calculate_group_standings():
    with get_db() as db:
        teams = db.query(Team).filter(Team.group_letter != None, Team.group_letter != "").all()
        matches = db.query(Match).filter(Match.status == "FINISHED", Match.group_letter != None, Match.group_letter != "").all()

        stats = {t.name: {"name": t.name, "gl": t.group_letter, "mp": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0} for t in teams}

        for m in matches:
            h_name = db.get(Team, m.home_team_id).name if m.home_team_id else None
            a_name = db.get(Team, m.away_team_id).name if m.away_team_id else None
            h_sc = m.home_score or 0
            a_sc = m.away_score or 0

            if h_name in stats:
                stats[h_name]["mp"] += 1
                stats[h_name]["gf"] += h_sc
                stats[h_name]["ga"] += a_sc
                if h_sc > a_sc:
                    stats[h_name]["w"] += 1
                    stats[h_name]["pts"] += 3
                elif h_sc == a_sc:
                    stats[h_name]["d"] += 1
                    stats[h_name]["pts"] += 1
                else:
                    stats[h_name]["l"] += 1

            if a_name in stats:
                stats[a_name]["mp"] += 1
                stats[a_name]["gf"] += a_sc
                stats[a_name]["ga"] += h_sc
                if a_sc > h_sc:
                    stats[a_name]["w"] += 1
                    stats[a_name]["pts"] += 3
                elif a_sc == h_sc:
                    stats[a_name]["d"] += 1
                    stats[a_name]["pts"] += 1
                else:
                    stats[a_name]["l"] += 1

        groups = {}
        for name, data in stats.items():
            data["gd"] = data["gf"] - data["ga"]
            letter = data["gl"].strip()[-1] if data["gl"] else ""
            if letter:
                groups.setdefault(letter, []).append(data)

        for gl in groups:
            groups[gl].sort(key=lambda x: (x["pts"], x["gd"], x["gf"]), reverse=True)

        return groups

# ── Render Logic ──────────────────────────────────────────────────────
def render():
    inject_css()
    require_login()

    page_header("MATCHES", "Official FIFA World Cup 2026 Calendar")

    all_matches = _load_all_matches()

    if not all_matches:
        st.info("No match data yet. Go to Admin → Data Sync to load fixtures.")
        return

    tab_matches, tab_groups = st.tabs(["Fixtures & Results", "Group Standings"])

    # ── TAB 1: MATCHES ───────────────────────────────────────────────
    with tab_matches:
        with st.expander("Search Matches", expanded=True):
            fc1, fc2 = st.columns(2)
            with fc1:
                team_names   = _load_team_names()
                team_filter  = st.selectbox("Search by Team", ["All Teams"] + team_names)
            with fc2:
                status_filter = st.selectbox("Status", ["All", "Scheduled", "Finished", "Live"])

        filtered = all_matches
        if team_filter != "All Teams":
            filtered = [m for m in filtered if team_filter in (m["home_name"], m["away_name"])]
        if status_filter == "Scheduled":
            filtered = [m for m in filtered if m["status"] in ("SCHEDULED", "TIMED")]
        elif status_filter == "Finished":
            filtered = [m for m in filtered if m["status"] == "FINISHED"]
        elif status_filter == "Live":
            filtered = [m for m in filtered if m["status"] in ("IN_PLAY", "PAUSED")]
       
        st.markdown(f"<p style='color:var(--text-muted);margin-bottom:20px;'>Showing {len(filtered)} matches</p>", unsafe_allow_html=True)

        by_date = {}
        for m in filtered:
            d = m["kickoff_time"].date() if isinstance(m["kickoff_time"], datetime) else None
            by_date.setdefault(d, []).append(m)

        for d in sorted(by_date.keys(), key=lambda x: x or date.max):
            d_label = d.strftime("%A, %d %B %Y") if d else "Date TBD"
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:12px;margin:30px 0 10px 0;border-bottom:1px solid var(--border);padding-bottom:8px;'>"
                f"<h3 style='margin:0;color:var(--secondary);'>{d_label}</h3>"
                f"</div>",
                unsafe_allow_html=True,
            )
            for m in by_date[d]:
                _render_match_row(m)

    # ── TAB 2: GROUPS ────────────────────────────────────────────────
    with tab_groups:
        groups_data = _calculate_group_standings()
        if not groups_data:
            st.info("Group data is not available yet.")
        else:
            for gl in sorted(groups_data.keys()):
                _render_group_table(gl, groups_data[gl])


def _render_match_row(m):
    home_flag = _flag_img(m["home_name"], 36)
    away_flag = _flag_img(m["away_name"], 36)
    
    h_sc = m["home_score"]
    a_sc = m["away_score"]
    k_time = format_kickoff(m["kickoff_time"])

    if m["status"] == "FINISHED":
        score_display = (
            f"<div style='font-size:1.8rem;font-weight:900;letter-spacing:1px;color:var(--secondary);'>{h_sc} - {a_sc}</div>"
            f"<div style='color:var(--text-muted);font-size:0.7rem;font-weight:700;margin-top:2px;'>FINAL</div>"
        )
    elif m["status"] in ("IN_PLAY", "PAUSED"):
        hs = h_sc if h_sc is not None else 0
        ast = a_sc if a_sc is not None else 0
        score_display = (
            f"<div style='font-size:1.8rem;font-weight:900;letter-spacing:1px;color:var(--primary);'>{hs} - {ast}</div>"
            f"<div style='color:var(--primary);font-size:0.7rem;font-weight:700;margin-top:2px;'>LIVE</div>"
        )
    else:
        score_display = (
            f"<div style='font-size:1rem;font-weight:800;color:var(--text-dim);margin-bottom:4px;'>VS</div>"
            f"<div style='font-size:0.7rem;color:var(--text-muted);'>{k_time}</div>"
        )

    stage_str = m['stage'].name if hasattr(m['stage'], 'name') else str(m['stage'])
    clean_stage = stage_str.replace("MatchStage.", "").replace("_", " ").title()
    stage_label = f"Group {m['group_letter']}" if m['group_letter'] else clean_stage

    card_html = (
        "<div style='background:var(--surface2);border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:10px;display:flex;align-items:center;justify-content:space-between;transition:border-color 0.15s;' onmouseover=\"this.style.borderColor='var(--primary)'\" onmouseout=\"this.style.borderColor='var(--border)'\">"
        "<div style='flex:1;display:flex;flex-direction:column;align-items:flex-end;'>"
        f"<div>{home_flag}</div>"
        f"<span style='font-weight:700;font-size:1rem;margin-top:6px;text-align:right;'>{m['home_name']}</span>"
        "</div>"
        f"<div style='flex:0.8;text-align:center;padding:0 10px;'>{score_display}</div>"
        "<div style='flex:1;display:flex;flex-direction:column;align-items:flex-start;'>"
        f"<div>{away_flag}</div>"
        f"<span style='font-weight:700;font-size:1rem;margin-top:6px;'>{m['away_name']}</span>"
        "</div>"
        "</div>"
        f"<div style='text-align:center;font-size:0.78rem;color:var(--text-muted);margin-top:-6px;margin-bottom:20px;'>"
        f"{m['venue']} &nbsp;·&nbsp; <span style='color:var(--secondary);'>{stage_label}</span>"
        "</div>"
    )
    st.markdown(card_html, unsafe_allow_html=True)


def _render_group_table(group_letter, teams_data):
    st.markdown(f"<h3 style='margin-top:20px; color:var(--secondary);'>Group {group_letter}</h3>", unsafe_allow_html=True)
    
    rows = []
    for idx, t in enumerate(teams_data):
        row_bg = "background:var(--surface2);" if idx >= 2 else "background:rgba(212, 175, 55, 0.05);"
        border_bottom = "border-bottom:1px solid var(--border);" if idx < len(teams_data)-1 else ""
        gd_str = f"+{t['gd']}" if t['gd'] > 0 else str(t['gd'])
        flag = _flag_img(t["name"], 20)
        
        row_html = (
            f"<tr style='{row_bg} {border_bottom} font-size:0.9rem;'>"
            f"<td style='padding:12px 10px; font-weight:800; color:var(--text-muted);'>{idx + 1}</td>"
            f"<td style='padding:12px 10px; font-weight:700;'><div style='display:flex; align-items:center; gap:10px;'>{flag} {t['name']}</div></td>"
            f"<td style='padding:12px 10px; text-align:center;'>{t['mp']}</td>"
            f"<td style='padding:12px 10px; text-align:center; color:var(--text-muted);'>{t['w']}</td>"
            f"<td style='padding:12px 10px; text-align:center; color:var(--text-muted);'>{t['d']}</td>"
            f"<td style='padding:12px 10px; text-align:center; color:var(--text-muted);'>{t['l']}</td>"
            f"<td style='padding:12px 10px; text-align:center;'>{gd_str}</td>"
            f"<td style='padding:12px 10px; text-align:center; font-weight:800; font-size:1rem; color:var(--secondary);'>{t['pts']}</td>"
            "</tr>"
        )
        rows.append(row_html)

    rows_html = "".join(rows)

    table_html = (
        "<div style='border:1px solid var(--border); border-radius:10px; overflow:hidden; margin-bottom:30px;'>"
        "<table style='width:100%; border-collapse:collapse; text-align:left;'>"
        "<thead>"
        "<tr style='background:var(--surface3); color:var(--text-muted); font-size:0.75rem; text-transform:uppercase;'>"
        "<th style='padding:10px; width:5%;'>#</th>"
        "<th style='padding:10px; width:45%;'>Team</th>"
        "<th style='padding:10px; text-align:center; width:10%;'>MP</th>"
        "<th style='padding:10px; text-align:center; width:8%;'>W</th>"
        "<th style='padding:10px; text-align:center; width:8%;'>D</th>"
        "<th style='padding:10px; text-align:center; width:8%;'>L</th>"
        "<th style='padding:10px; text-align:center; width:8%;'>GD</th>"
        "<th style='padding:10px; text-align:center; width:8%;'>Pts</th>"
        "</tr>"
        "</thead>"
        f"<tbody>{rows_html}</tbody>"
        "</table>"
        "</div>"
    )
    
    st.markdown(table_html, unsafe_allow_html=True)
