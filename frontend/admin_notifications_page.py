"""
frontend/admin_notifications_page.py
-----------------------------------------
Announcement Manager: admins create, edit, delete, and publish/archive
announcements stored in the existing Supabase `announcements` table.
Published (active) announcements are surfaced to regular users elsewhere
in the app via backend.admin_data.get_active_announcements().

Reuses backend.admin_data (list_announcements, create_announcement,
update_announcement, set_announcement_active, delete_announcement)
unchanged.
"""

from __future__ import annotations

import streamlit as st

from backend.admin_data import (
    list_announcements,
    create_announcement,
    update_announcement,
    set_announcement_active,
    delete_announcement,
    AdminDataError,
)
from frontend.components import glass_card_open, glass_card_close, pill


def render_admin_notifications_page() -> None:
    """Render the full Announcement Manager page."""
    st.markdown("### 📣 Announcement Manager")

    admin = st.session_state.get("admin_user") or {}

    with st.expander("➕ New Announcement", expanded=False):
        with st.form("admin_new_announcement_form", clear_on_submit=True):
            title = st.text_input("Title")
            body = st.text_area("Body")
            submitted = st.form_submit_button("📤 Publish Announcement", use_container_width=True)
        if submitted:
            try:
                create_announcement(title, body, admin.get("id", ""))
                st.success("Announcement published.")
                st.rerun()
            except AdminDataError as exc:
                st.error(str(exc))

    st.markdown("---")

    try:
        df = list_announcements()
    except AdminDataError as exc:
        st.error(f"⚠️ Could not load announcements: {exc}")
        return

    if df.empty:
        glass_card_open()
        st.markdown("<p class='muted'>No announcements yet.</p>", unsafe_allow_html=True)
        glass_card_close()
        return

    for _, row in df.iterrows():
        announcement_id = row["id"]
        glass_card_open()

        header = st.columns([3, 1])
        with header[0]:
            status_pill = pill("Active", "pill-high") if row.get("is_active") else pill("Archived", "pill-medium")
            st.markdown(f"**{row.get('title', '')}** {status_pill}", unsafe_allow_html=True)
            st.caption(str(row.get("created_at", ""))[:19])

        edit_key = f"admin_ann_edit_mode_{announcement_id}"
        if st.session_state.get(edit_key):
            with st.form(f"admin_ann_edit_form_{announcement_id}"):
                new_title = st.text_input("Title", value=row.get("title", ""))
                new_body = st.text_area("Body", value=row.get("body", ""))
                save = st.form_submit_button("💾 Save Changes")
            if save:
                try:
                    update_announcement(announcement_id, new_title, new_body)
                    st.session_state[edit_key] = False
                    st.success("Announcement updated.")
                    st.rerun()
                except AdminDataError as exc:
                    st.error(str(exc))
        else:
            st.write(row.get("body", ""))

        actions = st.columns(3)
        if actions[0].button("✏️ Edit", key=f"admin_ann_edit_btn_{announcement_id}", use_container_width=True):
            st.session_state[edit_key] = not st.session_state.get(edit_key, False)
            st.rerun()

        if row.get("is_active"):
            if actions[1].button("📥 Archive", key=f"admin_ann_archive_{announcement_id}", use_container_width=True):
                try:
                    set_announcement_active(announcement_id, False)
                    st.rerun()
                except AdminDataError as exc:
                    st.error(str(exc))
        else:
            if actions[1].button("📤 Publish", key=f"admin_ann_publish_{announcement_id}", use_container_width=True):
                try:
                    set_announcement_active(announcement_id, True)
                    st.rerun()
                except AdminDataError as exc:
                    st.error(str(exc))

        if actions[2].button("🗑️ Delete", key=f"admin_ann_delete_{announcement_id}", use_container_width=True):
            try:
                delete_announcement(announcement_id)
                st.rerun()
            except AdminDataError as exc:
                st.error(str(exc))

        glass_card_close()
