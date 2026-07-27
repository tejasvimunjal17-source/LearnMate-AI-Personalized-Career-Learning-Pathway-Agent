"""
frontend/notification_center.py
------------------------------------
User-facing Notification Center: an unread-count badge plus an expandable
panel listing notification history (broadcast + direct-to-them), with
mark-as-read support. Reads/writes only backend.notification_store.

Designed to be called once per authenticated page load from app.py's
sidebar — see render_notification_center().
"""

from __future__ import annotations

import streamlit as st

from backend.notification_store import (
    get_notifications_for_user,
    get_unread_count,
    mark_notification_read,
    mark_all_read,
    NotificationStoreError,
)


def render_notification_bell_and_panel() -> None:
    """Render the notification badge + an expander with full history.
    Call this once inside the authenticated sidebar, after auth_user exists."""
    user = st.session_state.get("auth_user")
    if not user:
        return

    email = user["email"]
    unread = get_unread_count(email)  # never raises - returns 0 on failure
    label = f"🔔 Notifications ({unread})" if unread else "🔔 Notifications"

    with st.expander(label, expanded=False):
        try:
            notifications = get_notifications_for_user(email)
        except NotificationStoreError as exc:
            st.error(f"⚠️ Could not load notifications: {exc}")
            return

        if not notifications:
            st.markdown("<p class='muted' style='margin:0;'>No notifications yet.</p>", unsafe_allow_html=True)
            return

        if unread:
            if st.button("✅ Mark all as read", key="notif_mark_all_read", use_container_width=True):
                try:
                    mark_all_read(email)
                    st.rerun()
                except NotificationStoreError as exc:
                    st.error(str(exc))

        for n in notifications:
            is_read = n.get("is_read", False)
            timestamp = str(n.get("created_at", ""))[:16]
            dot = "" if is_read else "🔵 "
            weight = "normal" if is_read else "600"
            st.markdown(
                f"<div style='padding:6px 0; border-bottom:1px solid rgba(128,128,128,0.15);'>"
                f"<span style='font-weight:{weight};'>{dot}{n.get('title', '')}</span> "
                f"<span class='muted mono' style='font-size:0.75rem;'>{timestamp}</span><br/>"
                f"<span style='font-size:0.9rem;'>{n.get('message', '')}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if not is_read:
                if st.button("Mark read", key=f"notif_read_{n['id']}", use_container_width=True):
                    try:
                        mark_notification_read(n["id"], email)
                        st.rerun()
                    except NotificationStoreError as exc:
                        st.error(str(exc))
