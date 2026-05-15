"""
pages/teams_page.py - Teams Directory & Profiles
Contains official FIFA historical data, recent form, and news integration.
"""
import streamlit as st
from database import get_db
from models import Team
from api.football_api import get_team_recent_matches
from utils.ui import inject_css, page_header, require_login

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
    "Curaçao":"cw", "Cape Verde Islands":"cv", "Norway":"no", "Jordan":"jo","TBD": ""
}

def _flag_img(team_name, size=40):
    code = COUNTRY_CODE.get(team_name.strip() if team_name else "", "")
    if code: return f"<img src='https://flagcdn.com/h40/{code}.png' style='width:{int(size*1.35)}px; height:{size}px; object-fit:cover; border-radius:6px; box-shadow:0 3px 6px rgba(0,0,0,0.3); vertical-align:middle;' />"
    if team_name.strip() == "TBD": return f"<span style='font-size:{size}px; line-height:1; color:var(--text-dim);'>❓</span>"
    return f"<span style='font-size:{size}px; line-height:1;'>🏳️</span>"

TEAM_HISTORY = {
    "Brazil": {"apps": "22", "titles": "5", "wc2022": "Quarter-Finals"},
    "Germany": {"apps": "20", "titles": "4", "wc2022": "Group Stage"},
    "Italy": {"apps": "18", "titles": "4", "wc2022": "Did Not Qualify"},
    "Argentina": {"apps": "18", "titles": "3", "wc2022": "Winners 🏆"},
    "France": {"apps": "16", "titles": "2", "wc2022": "Runner-up 🥈"},
    "Uruguay": {"apps": "14", "titles": "2", "wc2022": "Group Stage"},
    "England": {"apps": "16", "titles": "1", "wc2022": "Quarter-Finals"},
    "Spain": {"apps": "16", "titles": "1", "wc2022": "Round of 16"},
    "Netherlands": {"apps": "11", "titles": "0", "wc2022": "Quarter-Finals"},
    "Portugal": {"apps": "8", "titles": "0", "wc2022": "Quarter-Finals"},
    "Croatia": {"apps": "6", "titles": "0", "wc2022": "Third Place 🥉"},
    "Belgium": {"apps": "14", "titles": "0", "wc2022": "Group Stage"},
    "Switzerland": {"apps": "12", "titles": "0", "wc2022": "Round of 16"},
    "Denmark": {"apps": "6", "titles": "0", "wc2022": "Group Stage"},
    "Sweden": {"apps": "12", "titles": "0", "wc2022": "Did Not Qualify"},
    "Poland": {"apps": "9", "titles": "0", "wc2022": "Round of 16"},
    "Serbia": {"apps": "13", "titles": "0", "wc2022": "Group Stage"},
    "Austria": {"apps": "7", "titles": "0", "wc2022": "Did Not Qualify"},
    "Hungary": {"apps": "9", "titles": "0", "wc2022": "Did Not Qualify"},
    "Czechia": {"apps": "9", "titles": "0", "wc2022": "Did Not Qualify"},
    "Scotland": {"apps": "8", "titles": "0", "wc2022": "Did Not Qualify"},
    "Wales": {"apps": "2", "titles": "0", "wc2022": "Group Stage"},
    "Turkey": {"apps": "2", "titles": "0", "wc2022": "Did Not Qualify"},
    "Ukraine": {"apps": "1", "titles": "0", "wc2022": "Did Not Qualify"},
    "Norway": {"apps": "3", "titles": "0", "wc2022": "Did Not Qualify"},
    "Bosnia-Herzegovina": {"apps": "1", "titles": "0", "wc2022": "Did Not Qualify"},
    "USA": {"apps": "11", "titles": "0", "wc2022": "Round of 16"},
    "Mexico": {"apps": "17", "titles": "0", "wc2022": "Group Stage"},
    "Canada": {"apps": "2", "titles": "0", "wc2022": "Group Stage"},
    "Costa Rica": {"apps": "6", "titles": "0", "wc2022": "Group Stage"},
    "Colombia": {"apps": "6", "titles": "0", "wc2022": "Did Not Qualify"},
    "Chile": {"apps": "9", "titles": "0", "wc2022": "Did Not Qualify"},
    "Peru": {"apps": "5", "titles": "0", "wc2022": "Did Not Qualify"},
    "Ecuador": {"apps": "4", "titles": "0", "wc2022": "Group Stage"},
    "Paraguay": {"apps": "8", "titles": "0", "wc2022": "Did Not Qualify"},
    "Bolivia": {"apps": "3", "titles": "0", "wc2022": "Did Not Qualify"},
    "Venezuela": {"apps": "0", "titles": "0", "wc2022": "Did Not Qualify"},
    "Panama": {"apps": "1", "titles": "0", "wc2022": "Did Not Qualify"},
    "Jamaica": {"apps": "1", "titles": "0", "wc2022": "Did Not Qualify"},
    "Honduras": {"apps": "3", "titles": "0", "wc2022": "Did Not Qualify"},
    "El Salvador": {"apps": "2", "titles": "0", "wc2022": "Did Not Qualify"},
    "Haiti": {"apps": "1", "titles": "0", "wc2022": "Did Not Qualify"},
    "Curaçao": {"apps": "0", "titles": "0", "wc2022": "Did Not Qualify"},
    "Japan": {"apps": "7", "titles": "0", "wc2022": "Round of 16"},
    "South Korea": {"apps": "11", "titles": "0", "wc2022": "Round of 16"},
    "Morocco": {"apps": "6", "titles": "0", "wc2022": "Fourth Place"},
    "Senegal": {"apps": "3", "titles": "0", "wc2022": "Round of 16"},
    "Australia": {"apps": "6", "titles": "0", "wc2022": "Round of 16"},
    "Iran": {"apps": "6", "titles": "0", "wc2022": "Group Stage"},
    "Saudi Arabia": {"apps": "6", "titles": "0", "wc2022": "Group Stage"},
    "Cameroon": {"apps": "8", "titles": "0", "wc2022": "Group Stage"},
    "Nigeria": {"apps": "6", "titles": "0", "wc2022": "Did Not Qualify"},
    "Ghana": {"apps": "4", "titles": "0", "wc2022": "Group Stage"},
    "Ivory Coast": {"apps": "3", "titles": "0", "wc2022": "Did Not Qualify"},
    "Qatar": {"apps": "1", "titles": "0", "wc2022": "Group Stage"},
    "Tunisia": {"apps": "6", "titles": "0", "wc2022": "Group Stage"},
    "Algeria": {"apps": "4", "titles": "0", "wc2022": "Did Not Qualify"},
    "Egypt": {"apps": "3", "titles": "0", "wc2022": "Did Not Qualify"},
    "South Africa": {"apps": "3", "titles": "0", "wc2022": "Did Not Qualify"},
    "Congo DR": {"apps": "1", "titles": "0", "wc2022": "Did Not Qualify"},
    "Uzbekistan": {"apps": "0", "titles": "0", "wc2022": "Did Not Qualify"},
    "Mali": {"apps": "0", "titles": "0", "wc2022": "Did Not Qualify"},
    "Burkina Faso": {"apps": "0", "titles": "0", "wc2022": "Did Not Qualify"},
    "Iraq": {"apps": "1", "titles": "0", "wc2022": "Did Not Qualify"},
    "United Arab Emirates": {"apps": "1", "titles": "0", "wc2022": "Did Not Qualify"},
    "Oman": {"apps": "0", "titles": "0", "wc2022": "Did Not Qualify"},
    "China PR": {"apps": "1", "titles": "0", "wc2022": "Did Not Qualify"},
    "New Zealand": {"apps": "2", "titles": "0", "wc2022": "Did Not Qualify"},
    "Cape Verde Islands": {"apps": "0", "titles": "0", "wc2022": "Did Not Qualify"},
    "Jordan": {"apps": "0", "titles": "0", "wc2022": "Did Not Qualify"},
}

def _get_team_stats(team_name):
    aliases = {"United States":"USA", "Czech Republic":"Czechia", "Korea Republic":"South Korea", "IR Iran":"Iran"}
    normalized = aliases.get(team_name, team_name)
    return TEAM_HISTORY.get(normalized, {"apps":"0", "titles":"0", "wc2022":"Did Not Qualify"})

def _load_teams():
    with get_db() as db:
        teams = db.query(Team).filter(Team.name != "TBD").order_by(Team.name).all()
        return [{"id": t.id, "name": t.name, "tla": t.tla or ""} for t in teams]

def _load_recent_form(team_id):
    with get_db() as db:
        recent = get_team_recent_matches(db, team_id, limit=5)
    results = []
    for m in recent:
        hs, as_ = m.get("home_score"), m.get("away_score")
        ht = m.get("home_team", {})
        if hs is None or as_ is None: continue
        is_home = ht.get("id") == team_id
        if hs == as_: results.append("D")
        elif (is_home and hs > as_) or (not is_home and as_ > hs): results.append("W")
        else: results.append("L")
    while len(results) < 5: results.append("?")
    return results[:5]

def _render_form_html(form_list):
    html = "<div style='display:flex; gap:8px; align-items:center;'>"
    for res in form_list:
        bg = "#2E7D32" if res=="W" else "#757575" if res=="D" else "#C62828" if res=="L" else "var(--surface3)"
        color = "white" if res in ["W", "D", "L"] else "var(--text-muted)"
        html += f"<div style='background:{bg}; color:{color}; font-size:0.8rem; font-weight:bold; width:30px; height:30px; border-radius:50%; display:flex; align-items:center; justify-content:center; box-shadow:0 2px 4px rgba(0,0,0,0.2);'>{res}</div>"
    return html + "</div>"

def render():
    inject_css()
    require_login()
    teams = _load_teams()
    if not teams:
        st.info("Teams not yet synced. Go to Admin → Data Sync.")
        return
    if "selected_team" not in st.session_state: st.session_state.selected_team = None
    if st.session_state.selected_team is None: _render_directory(teams)
    else: _render_profile(st.session_state.selected_team)

def _render_directory(teams):
    page_header("TEAMS", "Official Directory of Qualified Nations")
    st.markdown("<p style='color:var(--text-muted); margin-bottom:15px;'>Select a country to view their profile, history, and news.</p>", unsafe_allow_html=True)
    search = st.text_input("Search Team", placeholder="e.g. Brazil, Portugal...", label_visibility="collapsed")
    filtered = [t for t in teams if search.lower() in t["name"].lower()] if search else teams
    st.markdown("<hr style='margin:15px 0;'>", unsafe_allow_html=True)
    cols = st.columns(3)
    for idx, t in enumerate(filtered):
        with cols[idx % 3]:
            st.markdown(f"<div style='display:flex; align-items:center; justify-content:center; gap:10px; margin-bottom:5px;'>{_flag_img(t['name'], 24)} <b>{t['name']}</b></div>", unsafe_allow_html=True)
            if st.button("View Profile", key=f"btn_{t['id']}", use_container_width=True):
                st.session_state.selected_team = t
                st.rerun()

def _render_profile(team):
    # Injetamos o CSS aqui para evitar criar blocos vazios entre os títulos e os botões
    st.markdown("""
        <style>
        button[kind="primary"] {
            background: linear-gradient(135deg, #a63232 0%, #8c2a2a 100%) !important;
            color: #FFFFFF !important;
            border: 1px solid #732222 !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            letter-spacing: 0.8px !important;
            text-transform: uppercase !important;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2) !important;
            transition: all 0.2s ease !important;
            height: 80px !important;
            min-height: 80px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            margin-top: 0px !important;
        }
        button[kind="primary"]:hover {
            background: linear-gradient(135deg, #b83d3d 0%, #9e3131 100%) !important;
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.3) !important;
            transform: translateY(-1px) !important;
        }
        button[kind="primary"] p {
            color: #FFFFFF !important;
            font-size: 1.05rem !important;
            margin: 0 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    if st.button("⬅️ Back to Directory", use_container_width=False):
        st.session_state.selected_team = None
        st.rerun()
    
    t_name, t_id = team["name"], team["id"]
    stats = _get_team_stats(t_name)
    
    st.markdown(f"""
        <div style="background:linear-gradient(135deg, var(--surface2) 0%, var(--surface1) 100%); 
                    border:1px solid var(--border); border-radius:15px; padding:30px; 
                    display:flex; flex-direction:column; align-items:center; justify-content:center;
                    margin:20px 0; width:100%; box-sizing:border-box;">
            <div style="margin-bottom:15px; display:flex; justify-content:center; width:100%;">
                {_flag_img(t_name, 80)}
            </div>
            <div style="margin:0; font-size:2.5rem; font-weight:800; letter-spacing:1px; color:var(--text); text-align:center; width:100%;">
                {t_name.upper()}
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div style='background:var(--surface2); border:1px solid var(--border); border-radius:10px; padding:20px; text-align:center; height:120px; display:flex; flex-direction:column; justify-content:center;'><div style='color:var(--text-muted); font-size:0.75rem; font-weight:800; text-transform:uppercase; margin-bottom:5px;'>World Cup Apps</div><div style='font-size:1.5rem; font-weight:900; color:var(--secondary);'>{stats['apps']}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div style='background:var(--surface2); border:1px solid var(--border); border-radius:10px; padding:20px; text-align:center; height:120px; display:flex; flex-direction:column; justify-content:center;'><div style='color:var(--text-muted); font-size:0.75rem; font-weight:800; text-transform:uppercase; margin-bottom:5px;'>World Cup Titles</div><div style='font-size:1.5rem; font-weight:900; color:var(--secondary);'>{stats['titles']}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div style='background:var(--surface2); border:1px solid var(--border); border-radius:10px; padding:20px; text-align:center; height:120px; display:flex; flex-direction:column; justify-content:center;'><div style='color:var(--text-muted); font-size:0.75rem; font-weight:800; text-transform:uppercase; margin-bottom:5px;'>2022 Performance</div><div style='font-size:1.1rem; font-weight:900; color:var(--secondary);'>{stats['wc2022']}</div></div>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    col_form, col_news = st.columns([1, 1])
    
    with col_form:
        st.markdown("<h4 style='margin-bottom:10px; color:var(--text);'>Recent Form (Last 5)</h4>", unsafe_allow_html=True)
        st.markdown(f"<div style='background:var(--surface2); border:1px solid var(--border); border-radius:10px; padding:20px; display:flex; justify-content:center; align-items:center; height:80px;'>{_render_form_html(_load_recent_form(t_id))}</div>", unsafe_allow_html=True)
        
    with col_news:
        st.markdown("<h4 style='margin-bottom:10px; color:var(--text);'>Media & Press</h4>", unsafe_allow_html=True)
        
        if st.button(f"ACCESS {t_name} NEWS", use_container_width=True, type="primary"):
            st.session_state.news_search_query = t_name
            st.session_state.search_query = t_name
            st.session_state.nav = "News"
            st.rerun()
