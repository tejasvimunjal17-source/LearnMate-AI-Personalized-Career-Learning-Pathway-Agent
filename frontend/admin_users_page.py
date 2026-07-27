"""
frontend/admin_users_page.py
--------------------------------
User Management: search users, view profile, enable/disable accounts, and
inspect a user's resume history, roadmap history, and AI chatbot requests.
No permanent deletion is exposed — disabling is the only status change
available, matching the spec.

Reuses backend.admin_data for users/roadmaps/resumes (unchanged). The
"AI requests" lookup queries backend.supabase_client's shared Supabase
client directly, since backend/admin_data.py doesn't yet expose a
per-user AI-response helper and this turn is scoped to this file only.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from backend.admin_data import (
    list_users,
    set_user_active,
    get_user_roadmap_history,
    get_user_resume_history,
    AdminDataError,
)
from backend.supabase_client import _get_client, SupabaseUnavailableError
from backend.logger_setup import get_logger
from frontend.components import glass_card_open, glass_card_close

logger = get_logger(__name__)


def _get_user_ai_requests(user_id: str) -> pd.DataFrame:
    """Fetch this user's AI Mentor chatbot exchanges from Supabase."""
    try:
        client = _get_client()
        resp = (
            client.table("ai_responses")
            .select("id, prompt, response, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return pd.DataFrame(resp.data or [])
    except SupabaseUnavailableError as exc:
        logger.warning("Supabase unavailable while fetching AI requests: %s", exc)
        return pd.DataFrame()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to fetch AI requests for user %s", user_id)
        return pd.DataFrame()


def _empty(message: str) -> None:
    st.markdown(f"<p class='muted'>{message}</p>", unsafe_allow_html=True)


def render_admin_users_page() -> None:
    """Render the full User Management page."""
    st.markdown("### 👥 User Management")

    try:
        users_df = list_users()
    except AdminDataError as exc:
        st.error(f"⚠️ Could not load users: {exc}")
        return

    if users_df.empty:
        glass_card_open()
        _empty("No registered users yet.")
        glass_card_close()
        return

    # --- Search ---
    glass_card_open("All Users")
    search_term = st.text_input(
        "🔎 Search users", key="admin_users_search", placeholder="Search by name or email…"
    )
    filtered_df = users_df
    if search_term:
        mask = filtered_df.apply(
            lambda row: row.astype(str).str.contains(search_term, case=False, na=False).any(), axis=1
        )
        filtered_df = filtered_df[mask]
    st.caption(f"**{len(filtered_df)}** user(s) match.")
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)
    glass_card_close()

    # --- Select a user to inspect ---
    st.markdown("---")
    st.markdown("#### 🔍 Inspect a User")

    if filtered_df.empty:
        _empty("No users match your search.")
        return

    options = {
        f"{row['first_name']} {row['last_name']} — {row['email']}": row["id"]
        for _, row in filtered_df.iterrows()
    }
    selected_label = st.selectbox("Select a user", options=list(options.keys()), key="admin_users_select")
    user_id = options[selected_label]
    user_row = users_df[users_df["id"] == user_id].iloc[0]

    # --- Profile card + enable/disable ---
    glass_card_open("Profile")
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"**Name**  \n{user_row['first_name']} {user_row['last_name']}")
    c2.markdown(f"**Email**  \n{user_row['email']}")
    is_active = bool(user_row.get("is_active", True))
    c3.markdown(f"**Status**  \n{'🟢 Active' if is_active else '🔴 Disabled'}")
    st.caption(f"Registered: {str(user_row.get('created_at', ''))[:19]}")

    if is_active:
        if st.button("🚫 Disable User", key=f"disable_{user_id}", use_container_width=True):
            try:
                set_user_active(user_id, False)
                st.success("User disabled.")
                st.rerun()
            except AdminDataError as exc:
                st.error(str(exc))
    else:
        if st.button("✅ Enable User", key=f"enable_{user_id}", use_container_width=True):
            try:
                set_user_active(user_id, True)
                st.success("User enabled.")
                st.rerun()
            except AdminDataError as exc:
                st.error(str(exc))
    glass_card_close()

    # --- History tabs ---
    tab_resume, tab_roadmap, tab_ai = st.tabs(["📄 Resume History", "🧭 Roadmap History", "🤖 AI Requests"])

    with tab_resume:
        try:
            resume_df = get_user_resume_history(user_id)
        except AdminDataError as exc:
            st.error(str(exc))
        else:
            if resume_df.empty:
                _empty("No resume profiles saved by this user yet.")
            else:
                st.dataframe(resume_df, use_container_width=True, hide_index=True)

    with tab_roadmap:
        try:
            roadmap_df = get_user_roadmap_history(user_id)
        except AdminDataError as exc:
            st.error(str(exc))
        else:
            if roadmap_df.empty:
                _empty("No roadmaps generated by this user yet.")
            else:
                st.dataframe(roadmap_df, use_container_width=True, hide_index=True)

    with tab_ai:
        ai_df = _get_user_ai_requests(user_id)
        if ai_df.empty:
            _empty("No AI Mentor requests logged for this user yet.")
        else:
            st.dataframe(ai_df, use_container_width=True, hide_index=True)
