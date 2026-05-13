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

from database import init_db, get_db
from api.football_api import sync_matches_to_db
from utils.ui import inject_css, GLOBAL_CSS, svg_icon
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
    initial_sidebar_state="expanded",
)

# ── Hide ALL Streamlit chrome: toolbar, hamburger, footer, deploy button ──
st.markdown("""
<style>
#MainMenu {visibility: hidden !important;}
header[data-testid="stHeader"] {display: none !important;}
footer {visibility: hidden !important;}
[data-testid="stToolbar"] {display: none !important;}
[data-testid="stDecoration"] {display: none !important;}
[data-testid="stStatusWidget"] {display: none !important;}
.viewerBadge_container__1QSob {display: none !important;}
button[title="View fullscreen"] {display: none !important;}
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
    auth_page.render()
    st.stop()

# ── Sidebar ─────────────────────────────────────────────
user = st.session_state.user
room = st.session_state.get("room")

NAV_OPTIONS = ["Dashboard", "Predictions", "Matches", "Teams", "Leaderboard", "Rooms", "News", "Admin"]

with st.sidebar:
    # ── Brand header ──
    st.markdown("""
        <div style="text-align:center;padding:18px 0 10px 0;">
            <div style="display:inline-flex;align-items:center;justify-content:center;
                width:48px;height:48px;border-radius:14px;
                background:linear-gradient(135deg,#E11D2E 0%,#B0121F 100%);
                box-shadow:0 8px 22px rgba(225,29,46,0.45);margin-bottom:10px;">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none"
                    stroke="#fff" stroke-width="2">
                    <polyline points="6 9 6 2 18 2 18 9"/>
                    <path d="M6 18H4a2 2 0 0 1-2-2v-1a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v1a2 2 0 0 1-2 2h-2"/>
                    <rect x="6" y="18" width="12" height="4"/>
                </svg>
            </div>
            <div style="font-family:'Bebas Neue',sans-serif;font-size:1.15rem;
                letter-spacing:2.5px;color:#F5F7FA;line-height:1.1;">WORLD CUP 2026</div>
            <div style="color:#F2C14E;font-size:0.62rem;letter-spacing:2px;
                margin-top:3px;font-weight:600;">PREDICTOR</div>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── User badge ──
    st.markdown(f"""
        <div style="background:#13161C;border:1px solid #262C36;border-radius:12px;
            padding:11px 12px;margin-bottom:10px;display:flex;align-items:center;gap:11px;">
            <div style="width:36px;height:36px;border-radius:50%;
                background:#1A1E26;display:flex;align-items:center;justify-content:center;
                font-size:1.2rem;border:1px solid #39414F;">{user['avatar_emoji']}</div>
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

    selected = st.radio(
        label="Navigation",
        options=NAV_OPTIONS,
        index=NAV_OPTIONS.index(st.session_state.nav),
        label_visibility="collapsed",
        key="nav_radio",
    )
    if selected != st.session_state.nav:
        st.session_state.nav = selected
        st.rerun()

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
