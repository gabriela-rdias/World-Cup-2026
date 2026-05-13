"""
pages/leaderboard_page.py - Leaderboard. All DB access inside session blocks.
"""
import streamlit as st
import pandas as pd
from database import get_db
from scoring import get_leaderboard
from utils.ui import inject_css, page_header, require_login, require_room


def render():
    inject_css()
    require_login()
    require_room()

    user = st.session_state.user
    room = st.session_state.room

    page_header("LEADERBOARD", f"Room: {room['name']}")

    with get_db() as db:
        lb = get_leaderboard(db, room["id"])

    if not lb:
        st.info("No players or scored predictions in this room yet.")
        return

    # Podium
    if len(lb) >= 2:
        _render_podium(lb[:min(3, len(lb))])

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Full Rankings")

    leader_pts = lb[0]["total_points"] if lb else 1

    for entry in lb:
        rank_labels = {1: "1st", 2: "2nd", 3: "3rd"}
        rank_label  = rank_labels.get(entry["rank"], f"#{entry['rank']}")
        is_me       = entry["user_id"] == user["id"]
        bg          = "#2A2A2A" if is_me else "#1E1E1E"
        border      = "1px solid #C8102E" if is_me else "1px solid #3A3A3A"
        pct         = (entry["total_points"] / leader_pts * 100) if leader_pts > 0 else 0

        st.markdown(
            f"""<div style="background:{bg};border:{border};border-radius:12px;
                padding:16px 20px;margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;
                    align-items:center;margin-bottom:8px;">
                    <div style="display:flex;align-items:center;gap:12px;">
                        <span style="font-size:1.2rem;min-width:36px;font-weight:700;">
                            {rank_label}
                        </span>
                        <span style="font-size:1.3rem;">{entry['avatar_emoji']}</span>
                        <div>
                            <div style="font-weight:700;font-size:0.95rem;">
                                {entry['username']}
                                {'<span style="color:#C8102E;font-size:0.72rem;"> (you)</span>' if is_me else ''}
                            </div>
                            <div style="color:#9A9A9A;font-size:0.72rem;margin-top:2px;">
                                Matches: <b>{entry['match_points']:.0f}</b> &nbsp;|&nbsp;
                                Groups: <b>{entry['group_points']:.0f}</b> &nbsp;|&nbsp;
                                Winner: <b>{entry['winner_points']:.0f}</b>
                            </div>
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:1.8rem;font-weight:800;color:#D4AF37;
                            font-family:'Bebas Neue',sans-serif;">
                            {entry['total_points']:.0f}
                        </div>
                        <div style="color:#9A9A9A;font-size:0.68rem;">points</div>
                    </div>
                </div>
                <div style="background:#141414;border-radius:4px;height:4px;overflow:hidden;">
                    <div style="background:linear-gradient(90deg,#C8102E,#D4AF37);
                        width:{pct:.1f}%;height:100%;border-radius:4px;"></div>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

    # Bar chart
    if len(lb) > 0:
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("Point Breakdown")
        df = pd.DataFrame(lb)[["username","match_points","group_points","winner_points"]]
        df.columns = ["Player","Match Points","Group Points","Winner Points"]
        st.bar_chart(df.set_index("Player"), use_container_width=True)


def _render_podium(top: list[dict]):
    order = []
    if len(top) >= 2: order.append(top[1])
    if len(top) >= 1: order.insert(len(order)//2, top[0])
    if len(top) >= 3: order.append(top[2])

    heights = {1: "110px", 2: "80px", 3: "60px"}
    medals  = {1: "1st", 2: "2nd", 3: "3rd"}

    cols = st.columns(len(order))
    for col, entry in zip(cols, order):
        h = heights.get(entry["rank"], "60px")
        m = medals.get(entry["rank"], "")
        with col:
            st.markdown(
                f"""<div style="text-align:center;">
                    <div style="font-size:2rem;">{entry['avatar_emoji']}</div>
                    <div style="font-weight:700;font-size:0.88rem;">{entry['username']}</div>
                    <div style="color:#D4AF37;font-weight:800;font-size:1.3rem;
                        font-family:'Bebas Neue',sans-serif;">{entry['total_points']:.0f} pts</div>
                    <div style="background:#2A2A2A;border:2px solid #D4AF37;
                        border-radius:8px 8px 0 0;height:{h};
                        display:flex;align-items:center;justify-content:center;
                        font-size:1.5rem;font-weight:800;color:#D4AF37;
                        margin-top:8px;">{m}</div>
                </div>""",
                unsafe_allow_html=True,
            )
