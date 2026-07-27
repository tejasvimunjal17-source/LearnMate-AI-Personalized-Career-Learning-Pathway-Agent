"""
frontend/admin_feedback_page.py
------------------------------------
Feedback Management: shows every feedback submission (message, rating,
user, timestamp) from the Supabase `feedback` table, and lets admins move
each item through Pending -> Reviewed -> Resolved.

Reuses backend.admin_data (fetch_table_df, update_feedback_status)
unchanged. Note: sql/002_feedback_enhancements.sql must be run in
Supabase for the `rating` column and the 3-state status constraint this
page relies on to exist. Until a user-facing feedback submission form is
added (none exists yet in the app), this page will honestly show an
empty state rather than fabricated rows.
"""

from __future__ import annotations

import streamlit as st

from backend.admin_data import fetch_table_df, update_feedback_status, AdminDataError
from frontend.components import glass_card_open, glass_card_close, pill

STATUS_OPTIONS = ["pending", "reviewed", "resolved"]
STATUS_PILL_CLASS = {"pending": "pill-medium", "reviewed": "pill-low", "resolved": "pill-high"}


def render_admin_feedback_page() -> None:
    """Render the full Feedback Management page."""
    st.markdown("### 💬 Feedback Management")

    try:
        df = fetch_table_df("Feedback")
    except AdminDataError as exc:
        st.error(f"⚠️ Could not load feedback: {exc}")
        return

    if df.empty:
        glass_card_open()
        st.markdown("<p class='muted'>No feedback submitted yet.</p>", unsafe_allow_html=True)
        glass_card_close()
        return

    status_filter = st.multiselect(
        "Filter by status",
        options=STATUS_OPTIONS,
        default=STATUS_OPTIONS,
        key="admin_feedback_status_filter",
    )
    filtered = df[df["status"].isin(status_filter)] if "status" in df.columns else df
    st.caption(f"**{len(filtered)}** feedback item(s)")
    st.markdown("---")

    if filtered.empty:
        glass_card_open()
        st.markdown("<p class='muted'>No feedback matches the selected filters.</p>", unsafe_allow_html=True)
        glass_card_close()
        return

    for _, row in filtered.sort_values("created_at", ascending=False).iterrows():
        glass_card_open()
        top = st.columns([3, 1])

        with top[0]:
            user_email = row.get("users.email", "") or "—"
            timestamp = str(row.get("created_at", ""))[:19]
            st.markdown(
                f"**{user_email}**  ·  <span class='muted mono' style='font-size:0.8rem;'>{timestamp}</span>",
                unsafe_allow_html=True,
            )
            rating = row.get("rating")
            if rating not in (None, "", "nan"):
                try:
                    st.markdown("⭐" * int(float(rating)))
                except (ValueError, TypeError):
                    pass
            st.write(row.get("message", ""))

        with top[1]:
            current_status = str(row.get("status", "pending"))
            st.markdown(
                pill(current_status.capitalize(), STATUS_PILL_CLASS.get(current_status, "")),
                unsafe_allow_html=True,
            )
            new_status = st.selectbox(
                "Update status",
                options=STATUS_OPTIONS,
                index=STATUS_OPTIONS.index(current_status) if current_status in STATUS_OPTIONS else 0,
                key=f"admin_feedback_status_{row['id']}",
                label_visibility="collapsed",
            )
            if new_status != current_status:
                if st.button("Save", key=f"admin_feedback_save_{row['id']}", use_container_width=True):
                    try:
                        update_feedback_status(row["id"], new_status)
                        st.success("Status updated.")
                        st.rerun()
                    except AdminDataError as exc:
                        st.error(str(exc))

        glass_card_close()
