"""
pages/auth_page.py — Login / Register with visual SVG avatar picker.
"""
import os, base64
import streamlit as st
from database import get_db
from utils.auth import register_user, login_user
from utils.ui import inject_css, svg_icon, FOOTBALL_AVATARS, AVATAR_LABELS, get_avatar_svg

def _trophy_b64():
    path = os.path.join(os.path.dirname(__file__), "..", "assets", "trophy.png")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

def render():
    inject_css()

    # ── Hero ───────────────────────────────────────────────────────────
    trophy_b64 = _trophy_b64()
    if trophy_b64:
        # filter:drop-shadow removes the white box background visually
        trophy_html = (
            f'<img src="data:image/png;base64,{trophy_b64}" '
            f'style="width:100px;height:auto;'
            f'filter:drop-shadow(0 6px 24px rgba(212,175,55,0.7)) brightness(1.05);'
            f'mix-blend-mode:normal;margin-bottom:10px;" />'
        )
    else:
        trophy_html = svg_icon("trophy", 64, "#D4AF37")

    st.markdown(f"""
        <div style="text-align:center;padding:48px 0 28px 0;">
            {trophy_html}
            <h1 style="font-size:3.4rem;margin:4px 0 0 0;letter-spacing:3px;
                background:linear-gradient(135deg,#FFFFFF 40%,#D4AF37 100%);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                WORLD CUP 2026
            </h1>
            <p style="color:var(--text-muted);font-size:0.95rem;margin:8px 0 0 0;letter-spacing:1px;">
                THE ULTIMATE PREDICTION GAME
            </p>
        </div>
    """, unsafe_allow_html=True)

    # ── Welcome card ───────────────────────────────────────────────────
    st.markdown(f"""
        <div style="background:var(--surface);border:1px solid var(--border);
            border-left:3px solid var(--primary);
            border-radius:var(--radius);padding:20px 26px;
            margin:0 auto 28px auto;max-width:700px;">
            <div style="font-size:1.05rem;font-weight:700;color:var(--text);margin-bottom:10px;">
                {svg_icon("globe",18,"#D4AF37")} &nbsp;Welcome to World Cup 2026 Predictor!
            </div>
            <div style="color:var(--text-muted);font-size:0.88rem;line-height:1.75;">
                Predict every match of <strong style="color:#D4AF37;">FIFA World Cup 2026</strong>
                and compete with your friends to see who knows football best.
                <br><br>
                <span style="color:var(--text);">How it works:</span>
                &nbsp;{svg_icon("check",14,"#2E7D32")} Predict results &nbsp;&nbsp;
                {svg_icon("check",14,"#2E7D32")} Call group standings &nbsp;&nbsp;
                {svg_icon("check",14,"#2E7D32")} Join private rooms &nbsp;&nbsp;
                {svg_icon("check",14,"#2E7D32")} Climb the leaderboard
            </div>
        </div>
    """, unsafe_allow_html=True)

    # ── Auth tabs ──────────────────────────────────────────────────────
    col_left, col_mid, col_right = st.columns([1, 2, 1])
    with col_mid:
        tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

        with tab_login:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.form("login_form"):
                username  = st.text_input("Username", placeholder="your_username")
                password  = st.text_input("Password", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("Sign In", use_container_width=True)
            if submitted:
                with get_db() as db:
                    ok, msg, user = login_user(db, username, password)
                if ok:
                    st.session_state.user = user
                    st.session_state.room = None
                    st.rerun()
                else:
                    st.error(msg)

        with tab_register:
            st.markdown("<br>", unsafe_allow_html=True)

            # ── Visual avatar picker ──────────────────────────────────
            if "selected_avatar" not in st.session_state:
                st.session_state.selected_avatar = AVATAR_LABELS[0]

            st.markdown(
                '<p style="color:var(--text-muted);font-size:0.82rem;font-weight:500;'
                'letter-spacing:0.3px;margin-bottom:8px;">PICK YOUR AVATAR</p>',
                unsafe_allow_html=True,
            )

            # Render avatar grid — 4 per row
            for row_start in range(0, len(FOOTBALL_AVATARS), 4):
                row_items = FOOTBALL_AVATARS[row_start:row_start+4]
                cols = st.columns(len(row_items))
                for col, (lbl, svg) in zip(cols, row_items):
                    with col:
                        is_sel = st.session_state.selected_avatar == lbl
                        border = "2px solid #B71C1C" if is_sel else "1px solid var(--border)"
                        bg     = "var(--surface3)" if is_sel else "var(--surface2)"
                        st.markdown(
                            f"""<div style="background:{bg};border:{border};border-radius:10px;
                                padding:10px;text-align:center;cursor:pointer;margin-bottom:4px;">
                                <div style="width:44px;height:44px;margin:0 auto;">{svg}</div>
                            </div>""",
                            unsafe_allow_html=True,
                        )
                        if st.button(lbl, key=f"av_{lbl}", use_container_width=True,
                                     help=f"Select {lbl}"):
                            st.session_state.selected_avatar = lbl
                            st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            with st.form("register_form", clear_on_submit=True):
                new_username = st.text_input("Username", placeholder="choose_a_username")
                new_email    = st.text_input("Email",    placeholder="you@example.com")
                new_password = st.text_input("Password", type="password",
                                             placeholder="min 6 characters")
                st.markdown(
                    f'<div style="padding:8px 0;font-size:0.82rem;color:var(--text-muted);">'
                    f'Selected avatar: <strong style="color:var(--text);">'
                    f'{st.session_state.selected_avatar}</strong></div>',
                    unsafe_allow_html=True,
                )
                submitted = st.form_submit_button("Create Account", use_container_width=True)

            if submitted:
                with get_db() as db:
                    ok, msg = register_user(
                        db, new_username, new_email, new_password,
                        st.session_state.selected_avatar,
                    )
                if ok:
                    st.success(msg + " Please sign in.")
                else:
                    st.error(msg)

    # ── Feature highlights ─────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    highlights = [
        ("matches",     "Predict Matches",   "Win / Draw / Loss for every game"),
        ("leaderboard", "Group Standings",   "Predict the final group table"),
        ("trophy",      "Pick the Winner",   "15 points for the champion"),
        ("star",        "Live Leaderboard",  "Compete with friends in real time"),
    ]
    for col, (ic, title, desc) in zip([c1,c2,c3,c4], highlights):
        with col:
            st.markdown(
                f"""<div style="background:var(--surface2);border:1px solid var(--border);
                    border-top:3px solid var(--secondary);border-radius:var(--radius);
                    padding:18px;text-align:center;">
                    <div style="margin-bottom:10px;">{svg_icon(ic,30,"#D4AF37")}</div>
                    <div style="font-weight:700;font-size:0.88rem;color:var(--text);
                        margin-bottom:4px;">{title}</div>
                    <div style="color:var(--text-muted);font-size:0.76rem;">{desc}</div>
                </div>""",
                unsafe_allow_html=True,
            )
