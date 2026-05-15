"""
app.py — FIFA World Cup 2026 Prediction Game — Main Streamlit Entry Point.
Run with:  streamlit run app.py
"""

import os
import logging
import streamlit as st
from PIL import Image as _PILImage
from dotenv import load_dotenv

load_dotenv()

# ── Inject Streamlit Cloud secrets into os.environ ─────
# st.secrets (set via the Streamlit Cloud dashboard) are NOT automatically
# available as environment variables. This block bridges that gap so that
# every module that reads os.environ (e.g. football_api.py) works on both
# local (.env file via load_dotenv) and Streamlit Cloud (st.secrets).
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str):
            os.environ.setdefault(_k, _v)
except Exception:
    pass  # No secrets configured — fine for local dev

from database import init_db, get_db
from api.football_api import sync_matches_to_db
from utils.ui import inject_css, GLOBAL_CSS, svg_icon, get_avatar_svg
from utils.auth import validate_session

from pages import auth_page, dashboard, matches_page, teams_page
from pages import leaderboard_page, predictions_page, rooms_page, admin_page, news_page

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s")
logger = logging.getLogger(__name__)

# ── Page config (must be first st call) ────────────────
_trophy_path = os.path.join(os.path.dirname(__file__), "assets", "trophy.png")
_trophy_icon = _PILImage.open(_trophy_path) if os.path.exists(_trophy_path) else "🏆"

st.set_page_config(
    page_title="World Cup 2026 Predictor",
    page_icon=_trophy_icon,
    layout="wide",
    initial_sidebar_state="expanded", # Arranca com a barra aberta
)

# ── Force dark mode (override OS / browser light theme) + hide chrome ─
st.markdown("""
<style>
:root { color-scheme: dark !important; }
html, body, [data-testid="stApp"] {
    background-color: #0B0D11 !important;
    color: #F5F7FA !important;
    color-scheme: dark !important;
}
@media (prefers-color-scheme: light) {
    html, body, [data-testid="stApp"], [data-testid="stAppViewContainer"] {
        background-color: #0B0D11 !important;
        color: #F5F7FA !important;
    }
}
#MainMenu {visibility: hidden !important;}
footer {visibility: hidden !important;}

/* Keep stHeader visible — they host the sidebar expand button on mobile */
header[data-testid="stHeader"] {
    background: transparent !important;
    display: flex !important;
    visibility: visible !important;
    z-index: 999 !important;
}
[data-testid="stToolbar"] {
    display: flex !important;
    visibility: visible !important;
    background: transparent !important;
}
[data-testid="stToolbarActions"], [data-testid="stDeployButton"], 
[data-testid="stDecoration"], [data-testid="stStatusWidget"], 
.viewerBadge_container__1QSob, button[title="View fullscreen"] {
    display: none !important;
}

/* Hide the default Streamlit page navigation list */
[data-testid="stSidebarNav"], [data-testid="stSidebarNavItems"], 
section[data-testid="stSidebar"] ul {
    display: none !important;
}

/* Remove the empty space left behind at the top of the sidebar */
section[data-testid="stSidebar"] > div > div:first-child {padding-top: 0rem !important;}

/* Shift the main page content to the very top */
[data-testid="stMain"] .block-container,
[data-testid="stMainBlockContainer"],
section.main > div.block-container,
.main .block-container {
    padding-top: 0rem !important;
    margin-top: -3.5rem !important; /* This pulls everything up into the empty space */
    padding-bottom: 1rem !important;
    max-width: 100% !important;
}

/* 🎯 ANIQUILAR O BOTÃO DE FECHAR A BARRA NO COMPUTADOR */
@media (min-width: 992px) {
    [data-testid="stSidebarCollapseButton"], 
    [data-testid="collapsedControl"] {
        display: none !important;
        visibility: hidden !important;
        width: 0px !important;
        height: 0px !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ── One-time startup ────────────────────────────────────
@st.cache_resource
def startup():
    logger.info("=== World Cup 2026 Predictor starting ===")
    init_db()
    logger.info("Database initialised.")
    if os.environ.get("FOOTBALL_API_KEY"):
        try:
            with get_db() as db:
                sync_matches_to_db(db)
            logger.info("Initial API sync complete.")
        except Exception as e:
            logger.warning(f"API sync failed (non-fatal): {e}")
    else:
        logger.info("No FOOTBALL_API_KEY — using local/demo data.")

startup()

# ── Session state defaults ──────────────────────────────
if "user" not in st.session_state:
    st.session_state.user = None
if "room" not in st.session_state:
    st.session_state.room = None
if "nav" not in st.session_state:
    st.session_state.nav = "Dashboard"

# ── Inject global CSS early ─────────────────────────────
inject_css()

# ── Auth gate ───────────────────────────────────────────
if st.session_state.user is None:
    # Ensure sidebar stays hidden on login page
    st.markdown("<style>[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)
    auth_page.render()
    st.stop()

# If we reached here, the user is logged in. 
# We show the sidebar and ensure it's not hidden by the CSS above.
st.markdown("<style>[data-testid='stSidebar'] {display: flex;}</style>", unsafe_allow_html=True)

# Validate that the logged-in user still exists and is active in the DB
with get_db() as _db:
    if not validate_session(_db):
        auth_page.render()
        st.stop()

# ── Sidebar ─────────────────────────────────────────────
user = st.session_state.user
room = st.session_state.get("room")

NAV_OPTIONS = ["Dashboard", "Predictions", "Matches", "Teams", "Leaderboard", "Rooms", "News"]

# Convert the trophy.png to base64 so it can be used in the HTML
import base64
def get_trophy_b64():
    if os.path.exists(_trophy_path):
        with open(_trophy_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

trophy_b64 = get_trophy_b64()
if trophy_b64:
    logo_html = f'<img src="data:image/png;base64,{trophy_b64}" style="width:64px;height:auto;filter:drop-shadow(0 4px 12px rgba(212,175,55,0.4));margin-bottom:10px;" />'
else:
    logo_html = '<div style="font-size:2.5rem;margin-bottom:10px;">🏆</div>'

with st.sidebar:
    # ── Brand header ──
    st.markdown(f"""
        <div style="text-align:center;padding:18px 0 10px 0;">
            {logo_html}
            <div style="font-family:'Bebas Neue',sans-serif;font-size:1.15rem;
                letter-spacing:2.5px;color:#F5F7FA;line-height:1.1;">WORLD CUP 2026</div>
            <div style="color:#F2C14E;font-size:0.62rem;letter-spacing:2px;
                margin-top:3px;font-weight:600;">PREDICTOR</div>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── User badge ──
    _avatar_svg = get_avatar_svg(user['avatar_emoji'], size=28)
    st.markdown(f"""
        <div style="background:#13161C;border:1px solid #262C36;border-radius:12px;
            padding:11px 12px;margin-bottom:10px;display:flex;align-items:center;gap:11px;">
            <div style="width:36px;height:36px;border-radius:50%;
                background:#1A1E26;display:flex;align-items:center;justify-content:center;
                font-size:1.2rem;border:1px solid #39414F;">{_avatar_svg}</div>
            <div style="min-width:0;">
                <div style="font-weight:600;font-size:0.9rem;color:#F5F7FA;
                    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{user['username']}</div>
                <div style="color:#22C55E;font-size:0.68rem;display:flex;align-items:center;gap:5px;">
                    <span style="width:6px;height:6px;border-radius:50%;background:#22C55E;display:inline-block;"></span>
                    Online
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # ── Active room badge ──
    if room:
        st.markdown(f"""
            <div style="background:linear-gradient(135deg,#1A1E26 0%,#13161C 100%);
                border:1px solid #39414F;border-radius:12px;
                padding:10px 12px;margin-bottom:10px;position:relative;overflow:hidden;">
                <div style="position:absolute;left:0;top:0;bottom:0;width:3px;background:#F2C14E;"></div>
                <div style="color:#F2C14E;font-size:0.62rem;font-weight:700;letter-spacing:1.4px;">
                    ACTIVE ROOM
                </div>
                <div style="font-size:0.92rem;font-weight:600;color:#F5F7FA;margin-top:3px;
                    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{room['name']}</div>
                <div style="color:#9AA3B2;font-size:0.7rem;margin-top:2px;font-family:monospace;">
                    {room['invite_code']}
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style="background:#13161C;border:1px dashed #39414F;
                border-radius:12px;padding:10px 12px;margin-bottom:10px;">
                <div style="color:#9AA3B2;font-size:0.78rem;">No room selected</div>
                <div style="color:#F2C14E;font-size:0.7rem;margin-top:3px;">Join or create one below</div>
            </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── Navigation — st.radio is the reliable Streamlit nav pattern ──
    st.markdown("""
    <style>
    [data-testid="stSidebar"] [data-testid="stRadio"] > div { gap: 2px !important; }
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        background: transparent !important;
        border-radius: 10px !important;
        padding: 10px 14px !important;
        cursor: pointer !important;
        color: #9AA3B2 !important;
        font-size: 0.92rem !important;
        font-weight: 500 !important;
        width: 100% !important;
        transition: all 0.15s !important;
        margin-bottom: 1px !important;
        display: flex !important;
        align-items: center !important;
        min-height: 42px !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        background: rgba(255,255,255,0.04) !important;
        color: #F5F7FA !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
        background: linear-gradient(90deg,#E11D2E 0%, #B0121F 100%) !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 14px rgba(225,29,46,0.35) !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child,
    [data-testid="stSidebar"] [data-testid="stRadio"] span[data-baseweb="radio"] {
        display: none !important;
    }
    /* Sign out button — ghost style in sidebar */
    [data-testid="stSidebar"] .stButton > button {
        background: transparent !important;
        color: #9AA3B2 !important;
        border: 1px solid #262C36 !important;
        border-radius: 10px !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        width: 100% !important;
        min-height: 40px !important;
        box-shadow: none !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(225,29,46,0.10) !important;
        color: #FF3B4D !important;
        border-color: #FF3B4D !important;
        transform: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

def update_nav():
    st.session_state.nav = st.session_state.nav_radio

if "nav_radio" not in st.session_state:
    st.session_state.nav_radio = st.session_state.nav

if st.session_state.nav_radio != st.session_state.nav:
    st.session_state.nav_radio = st.session_state.nav

with st.sidebar:
    st.radio(
        label="Navigation",
        options=NAV_OPTIONS,
        label_visibility="collapsed",
        key="nav_radio",
        on_change=update_nav
    )

    st.divider()

    if st.button("Sign Out", key="signout_btn", use_container_width=True):
        st.session_state.user = None
        st.session_state.room = None
        st.session_state.nav  = "Dashboard"
        st.rerun()

    st.markdown("""
        <div style="color:#5F6776;font-size:0.62rem;text-align:center;
            margin-top:18px;line-height:1.7;letter-spacing:0.5px;">
            FIFA WORLD CUP 2026<br>
            <span style="color:#39414F;">USA · CANADA · MEXICO</span>
        </div>
    """, unsafe_allow_html=True)

# ── Page routing ────────────────────────────────────────
page = st.session_state.nav

if   page == "Dashboard":   dashboard.render()
elif page == "Predictions": predictions_page.render()
elif page == "Matches":     matches_page.render()
elif page == "Teams":       teams_page.render()
elif page == "Leaderboard": leaderboard_page.render()
elif page == "Rooms":       rooms_page.render()
elif page == "News":        news_page.render()
elif page == "Admin":       admin_page.render()
else:
    st.error(f"Unknown page: {page}")
