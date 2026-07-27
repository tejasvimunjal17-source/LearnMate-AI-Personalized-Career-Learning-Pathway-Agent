"""
frontend/admin_broadcast_page.py
-------------------------------------
Admin UI for the Notification System (Phase 4, Part 1): send a broadcast
notification to every user, or a direct notification to one specific
user by email, plus a full send history with the ability to retract
(deactivate) a notification. Distinct from frontend/admin_notifications_page.py
(Phase 3), which manages the separate `announcements` table — untouched here.
"""

from __future__ import annotations

import streamlit as st

from backend.notification_store import (
    create_broadcast_notification,
    create_direct_notification,
    list_all_notifications,
    deactivate_notification,
    NotificationStoreError,
)
from frontend.components import glass_card_open, glass_card_close, pill


def render_admin_broadcast_page() -> None:
    st.markdown("### 🔔 Notification Center (Admin)")

    admin = st.session_state.get("admin_user") or {}

    glass_card_open("Send a Notification")
    with st.form("admin_send_notification_form", clear_on_submit=True):
        send_type = st.radio(
            "Send to", options=["Everyone (Broadcast)", "One User (Direct)"], horizontal=True
        )
        target_email = ""
        if send_type == "One User (Direct)":
            target_email = st.text_input("User's email")
        title = st.text_input("Title")
        message = st.text_area("Message")
        submitted = st.form_submit_button("📤 Send", use_container_width=True)

    if submitted:
        try:
            if send_type == "Everyone (Broadcast)":
                create_broadcast_notification(title, message, admin.get("id", ""))
            else:
                create_direct_notification(target_email, title, message, admin.get("id", ""))
            st.success("Notification sent.")
            st.rerun()
        except NotificationStoreError as exc:
            st.error(str(exc))
    glass_card_close()

    st.markdown("---")
    st.markdown("#### 🗂️ Notification History")

    try:
        notifications = list_all_notifications()
    except NotificationStoreError as exc:
        st.error(f"⚠️ Could not load notification history: {exc}")
        return

    if not notifications:
        glass_card_open()
        st.markdown("<p class='muted'>No notifications sent yet.</p>", unsafe_allow_html=True)
        glass_card_close()
        return

    for n in notifications:
        glass_card_open()
        top = st.columns([3, 1])
        with top[0]:
            recipient = "Everyone" if n.get("type") == "broadcast" else ((n.get("users") or {}).get("email") or "—")
            status_pill = pill("Active", "pill-high") if n.get("is_active") else pill("Retracted", "pill-medium")
            st.markdown(f"**{n.get('title', '')}** {status_pill}", unsafe_allow_html=True)
            st.caption(f"To: {recipient} · {str(n.get('created_at', ''))[:19]}")
            st.write(n.get("message", ""))
        with top[1]:
            if n.get("is_active"):
                if st.button("🚫 Retract", key=f"notif_retract_{n['id']}", use_container_width=True):
                    try:
                        deactivate_notification(n["id"])
                        st.rerun()
                    except NotificationStoreError as exc:
                        st.error(str(exc))
        glass_card_close()
