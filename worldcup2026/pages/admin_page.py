"""
pages/admin_page.py — Admin panel. SVG icons, 2022 World Cup real data mode.
"""
import streamlit as st
from datetime import datetime
from database import get_db
from models import Match, Room, User, Team, MatchStage
from scoring import (
    score_match_predictions, score_group_standings,
    score_tournament_winner, recalculate_all_points, get_leaderboard,
)
from api.football_api import sync_matches_to_db, _fallback_teams
from utils.ui import inject_css, page_header, require_login, require_room, get_avatar_svg
from utils.svg_icons import icon
from utils.wc2022_data import (
    WC2022_TEAMS, GROUP_MATCHES, KNOCKOUT_MATCHES,
    GROUP_STANDINGS_2022, WINNER_2022, TEAM_FLAGS, get_team_by_id,
)


def _ic(name, sz=16, col="#FFD0D0"):
    return icon(name, sz, col)


def render():
    inject_css()
    require_login()
    require_room()

    user = st.session_state.user
    room = st.session_state.room

    page_header("ADMIN", f"Room: {room['name']}")

    is_owner = room["owner_id"] == user["id"]
    if not is_owner:
        st.warning("⚠️ Only the room owner can access admin tools.")
        st.info("Contact the room owner to trigger scoring or sync data.")
        _show_readonly_stats(room)
        return

    st.success("👑 You are the room owner. Full admin access granted.")

    tab_sync, tab_score, tab_wc2022, tab_members, tab_export = st.tabs([
        "Data Sync",
        "Scoring",
        "WC 2022 Mode",
        "Members",
        "Export Data",
    ])


    # ── DATA SYNC ────────────────────────────────────────
    with tab_sync:
        st.subheader("Sync Match Data from API")
        st.markdown("Pull the latest match results and team data from the football API.")
        st.info("💡 Data is automatically cached for 1–24 hours to respect API rate limits.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Sync All Matches", use_container_width=True):
                with st.spinner("Fetching match data from API…"):
                    with get_db() as db:
                        sync_matches_to_db(db)
                st.success(f"✅ Match data synced successfully!")
                st.rerun()
        with col2:
            if st.button("Clear API Cache", use_container_width=True):
                with get_db() as db:
                    from models import APICache
                    db.query(APICache).delete()
                st.success("Cache cleared. Next sync will fetch fresh data.")

        with get_db() as db:
            total_matches    = db.query(Match).count()
            finished_matches = db.query(Match).filter(Match.status == "FINISHED").count()
            live_matches     = db.query(Match).filter(Match.status.in_(["IN_PLAY","PAUSED"])).count()
            scheduled        = db.query(Match).filter(Match.status == "SCHEDULED").count()
            total_teams      = db.query(Team).count()

        st.markdown("---")
        st.subheader("Database Status")
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Total Matches",   total_matches)
        c2.metric("Finished",        finished_matches)
        c3.metric("Live",            live_matches)
        c4.metric("Scheduled",       scheduled)
        c5.metric("Teams",           total_teams)

    # ── SCORING ──────────────────────────────────────────
    with tab_score:
        st.subheader("Run Scoring Engine")
        st.markdown("Trigger the scoring engine to evaluate predictions against actual results.")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Match Predictions**")
            if st.button("Score All Finished Matches", use_container_width=True):
                with get_db() as db:
                    finished = (db.query(Match)
                        .filter(Match.status == "FINISHED", Match.result.isnot(None)).all())
                    total_scored = sum(score_match_predictions(db, m) for m in finished)
                st.success(f"✅ Scored {total_scored} match predictions.")
                st.rerun()

        with col2:
            st.markdown("**Group Standings**")
            groups_available = _get_completed_groups()
            if groups_available:
                selected_group = st.selectbox("Select group to score", options=groups_available, key="score_group_select")
                if st.button("Score Group Standings", use_container_width=True):
                    with get_db() as db:
                        n = score_group_standings(db, selected_group, room["id"])
                    st.success(f"✅ Scored {n} group standing predictions for Group {selected_group}.")
                    st.rerun()
            else:
                st.info("No completed groups to score yet.")

        st.markdown("---")
        st.markdown("**Tournament Winner**")
        col3, col4 = st.columns(2)
        with col3:
            teams = _fallback_teams()
            team_options = {t["name"]: t["id"] for t in sorted(teams, key=lambda x: x["name"])}
            winner_team = st.selectbox("Select actual tournament winner", options=list(team_options.keys()))
        with col4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Award Winner Points (15 pts)", use_container_width=True):
                with get_db() as db:
                    n = score_tournament_winner(db, team_options[winner_team], room["id"])
                st.success(f"✅ Awarded winner points to {n} prediction(s).")
                st.rerun()

        st.markdown("---")
        st.markdown("**Recalculate All Points**")
        if st.button("Recalculate All Room Points", use_container_width=True):
            with get_db() as db:
                recalculate_all_points(db, room["id"])
            st.success(f"✅ All point totals recalculated.")
            st.rerun()

        st.markdown("---")
        st.subheader("Current Leaderboard")
        with get_db() as db:
            lb = get_leaderboard(db, room["id"])
        if lb:
            for entry in lb:
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:8px;padding:4px 0;">'
                    f'<b>#{entry["rank"]}</b>'
                    f'{get_avatar_svg(entry["avatar_emoji"], 22)}'
                    f'<span>{entry["username"]}</span>'
                    f'<span style="color:var(--text-muted);">— '
                    f'<b>{entry["total_points"]:.0f} pts</b> '
                    f'<i>(Matches: {entry["match_points"]:.0f} | '
                    f'Groups: {entry["group_points"]:.0f} | '
                    f'Winner: {entry["winner_points"]:.0f})</i></span></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No scored predictions yet.")

    # ── WC 2022 MODE ─────────────────────────────────────
    with tab_wc2022:
        st.subheader("World Cup 2022 — Qatar")
        st.markdown(
            "🌐 Load **real World Cup 2022 data** (Qatar) into the database. "
            "All 64 matches with authentic results — split across all scoring categories: "
            "group stage, knockouts, and tournament winner. You can predict on everything as if it's live."
        )

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("""
            **What gets loaded:**
            - 32 teams across 8 groups (A–H)
            - 48 group stage matches with real scores
            - 16 knockout matches (R16 → Final)
            - All results marked as FINISHED and scoreable
            - Tournament winner: Argentina
            """)
        with col_b:
            st.markdown("""
            **Scoring breakdown:**
            - Group match correct result → 1 pt each
            - Round of 16 correct → 2 pts each
            - Quarter-final correct → 6 pts each
            - Semi-final correct → 8 pts each
            - Final correct → 10 pts
            - Group standings (all 4 correct) → 3 pts
            - Tournament winner correct → 15 pts
            """)

        st.markdown("---")

        st.markdown("**Groups Preview**")
        groups_by_letter = {}
        for t in WC2022_TEAMS:
            groups_by_letter.setdefault(t["group"], []).append(t)

        cols = st.columns(4)
        for i, (grp, members) in enumerate(sorted(groups_by_letter.items())):
            with cols[i % 4]:
                members_str = " · ".join(
                    f"{TEAM_FLAGS.get(t['id'],'')} {t['tla']}" for t in members
                )
                st.markdown(
                    f"""<div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:10px;margin-bottom:8px;">
                    <div style="font-weight:700;color:#D4AF37;margin-bottom:4px;">Group {grp}</div>
                    <div style="font-size:0.78rem;color:#C4A4A4;">{members_str}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

        st.markdown("---")
        st.warning("⚠️ This will clear existing match/team data and replace it with WC 2022 data.")

        if st.button("Load World Cup 2022 Data", use_container_width=True):
            with st.spinner("Loading WC 2022 data…"):
                _insert_wc2022_data()
            st.success(f"✅ World Cup 2022 data loaded! Go to Matches or Predictions to explore.")
            st.rerun()

        st.markdown("---")
        st.markdown("**Simulate scoring for WC 2022**")
        st.caption("Run all scoring engines against the real 2022 results to award points to predictions already submitted.")
        if st.button("Score All WC 2022 Predictions", use_container_width=True):
            _score_wc2022(room["id"])
            st.success(f"✅ All WC 2022 predictions scored.")
            st.rerun()

    # ── MEMBERS ──────────────────────────────────────────
    with tab_members:
        st.subheader("Room Members")
        from utils.rooms import get_room_members
        from models import User as UserModel
        with get_db() as db:
            members = get_room_members(db, room["id"])
            member_users = [
                {
                    "username": db.get(UserModel, m.user_id).username if db.get(UserModel, m.user_id) else "Unknown",
                    "avatar":   db.get(UserModel, m.user_id).avatar_emoji if db.get(UserModel, m.user_id) else "⚽",
                    "points":   m.total_points or 0.0,
                    "joined":   m.joined_at.strftime("%d %b %Y") if m.joined_at else "—",
                    "is_owner": m.user_id == room["owner_id"],
                }
                for m in members
            ]
        if not member_users:
            st.info("No members yet.")
        else:
            for i, m in enumerate(member_users, 1):
                crown = " 👑" if m["is_owner"] else ""
                st.markdown(
                    f"""<div style="display:flex;align-items:center;gap:14px;
                        background:rgba(0,0,0,0.18);border-radius:10px;
                        padding:10px 16px;margin-bottom:6px;">
                        <div style="font-size:1.4rem;min-width:32px;text-align:center;">{m['avatar']}</div>
                        <div style="flex:1;">
                            <span style="font-weight:700;color:#F5F7FA;">{m['username']}</span>{crown}
                            <span style="color:#9AA3B2;font-size:0.78rem;margin-left:10px;">Joined {m['joined']}</span>
                        </div>
                        <div style="font-weight:700;color:#F2C14E;font-size:1rem;">{m['points']:.0f} pts</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

    # ── EXPORT DATA ──────────────────────────────────────
    with tab_export:
        st.markdown("**Export Room Data (Backup)**")
        st.caption("Download all predictions and scores as JSON — useful before any major change.")
        if st.button("Export Room Data", use_container_width=True):
            export = _export_room_data(room["id"])
            import json
            st.download_button(
                label="Download JSON backup",
                data=json.dumps(export, indent=2, default=str),
                file_name=f"wc2026_room_{room['id']}_backup.json",
                mime="application/json",
                use_container_width=True,
            )

# ── HELPERS ───────────────────────────────────────────────────────────

def _show_readonly_stats(room: dict):
    with get_db() as db:
        total = db.query(Match).count()
        fin   = db.query(Match).filter(Match.status == "FINISHED").count()
    st.metric("Total Matches", total)
    st.metric("Finished", fin)


def _get_completed_groups() -> list[str]:
    completed = []
    with get_db() as db:
        from sqlalchemy import func
        group_totals   = (db.query(Match.group_letter, func.count(Match.id).label("total"))
            .filter(Match.stage == MatchStage.GROUP, Match.group_letter != "")
            .group_by(Match.group_letter).all())
        group_finished = (db.query(Match.group_letter, func.count(Match.id).label("finished"))
            .filter(Match.stage == MatchStage.GROUP, Match.status == "FINISHED", Match.group_letter != "")
            .group_by(Match.group_letter).all())
        totals_map   = {g: n for g, n in group_totals}
        finished_map = {g: n for g, n in group_finished}
        for grp, total in totals_map.items():
            if finished_map.get(grp, 0) == total and total > 0:
                completed.append(grp)
    return sorted(completed)


def _insert_wc2022_data():
    """Clear existing data and insert real WC 2022 teams and matches."""
    with get_db() as db:
        # Clear existing teams and matches (keep predictions/rooms)
        db.query(Match).delete()
        db.query(Team).delete()

        # Insert teams
        for t in WC2022_TEAMS:
            team = Team(
                id           = t["id"],
                name         = t["name"],
                short_name   = t["shortName"],
                tla          = t["tla"],
                group_letter = t["group"],
                crest_url    = "",
            )
            db.add(team)

        # Insert group matches
        for mid, hid, aid, hs, as_, md, grp in GROUP_MATCHES:
            result = "home" if hs > as_ else ("away" if as_ > hs else "draw")
            db.add(Match(
                id           = mid,
                stage        = MatchStage.GROUP,
                group_letter = grp,
                matchday     = md,
                home_team_id = hid,
                away_team_id = aid,
                kickoff_time = datetime(2022, 11, 20 + (mid - 2001) // 4),
                status       = "FINISHED",
                home_score   = hs,
                away_score   = as_,
                result       = result,
            ))

        # Insert knockout matches
        ko_date = datetime(2022, 12, 3)
        for i, (mid, hid, aid, hs, as_, stage, _) in enumerate(KNOCKOUT_MATCHES):
            result = "home" if hs > as_ else ("away" if as_ > hs else "draw")
            db.add(Match(
                id           = mid,
                stage        = stage,
                group_letter = "",
                matchday     = 0,
                home_team_id = hid,
                away_team_id = aid,
                kickoff_time = datetime(2022, 12, 3 + i),
                status       = "FINISHED",
                home_score   = hs,
                away_score   = as_,
                result       = result,
            ))
        db.commit()


def _score_wc2022(room_id: int):
    """Run all scoring engines for WC 2022 matches."""
    with get_db() as db:
        finished = db.query(Match).filter(Match.status == "FINISHED", Match.result.isnot(None)).all()
        for match in finished:
            score_match_predictions(db, match)
        for grp, ranking in GROUP_STANDINGS_2022.items():
            score_group_standings(db, grp, room_id)
        score_tournament_winner(db, WINNER_2022, room_id)
        recalculate_all_points(db, room_id)


def _export_room_data(room_id: int) -> dict:
    """Fix #10: Export all room data to JSON for backup."""
    from models import MatchPrediction, GroupStagePrediction, TournamentWinnerPrediction, RoomMember, User as UserModel
    with get_db() as db:
        members = (db.query(RoomMember, UserModel)
                     .join(UserModel, RoomMember.user_id == UserModel.id)
                     .filter(RoomMember.room_id == room_id).all())
        match_preds = db.query(MatchPrediction).filter(MatchPrediction.room_id == room_id).all()
        group_preds = db.query(GroupStagePrediction).filter(GroupStagePrediction.room_id == room_id).all()
        winner_preds = db.query(TournamentWinnerPrediction).filter(TournamentWinnerPrediction.room_id == room_id).all()
        return {
            "room_id": room_id,
            "members": [{"user_id": u.id, "username": u.username, "total_points": m.total_points}
                        for m, u in members],
            "match_predictions": [{"user_id": p.user_id, "match_id": p.match_id,
                                    "predicted_result": p.predicted_result,
                                    "points_awarded": p.points_awarded,
                                    "is_scored": p.is_scored} for p in match_preds],
            "group_predictions": [{"user_id": p.user_id, "group_letter": p.group_letter,
                                    "team_id": p.team_id, "predicted_position": p.predicted_position,
                                    "points_awarded": p.points_awarded,
                                    "is_scored": p.is_scored} for p in group_preds],
            "winner_predictions": [{"user_id": p.user_id, "team_id": p.team_id,
                                     "points_awarded": p.points_awarded,
                                     "is_scored": p.is_scored} for p in winner_preds],
        }
