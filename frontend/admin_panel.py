"""
frontend/admin_panel.py
---------------------------
Admin Panel router. Gates on st.session_state["admin_user"] — completely
independent of the regular st.session_state["auth_user"] session used by
frontend/auth_page.py and the rest of the app. If no admin is logged in,
renders the Admin Login page; otherwise renders a sidebar nav (styled to
match the app's existing option_menu sidebar) that switches between the
five Admin Panel sections built so far.

This file does not wire itself into app.py — per this phase's scope, that
integration (adding the entry point / nav trigger) is a separate step.
Call render_admin_panel() from wherever the app decides to enter admin
mode.
"""

from __future__ import annotations

import streamlit as st
from streamlit_option_menu import option_menu

from frontend.admin_login_page import render_admin_login_page
from frontend.admin_dashboard_page import render_admin_dashboard_page
from frontend.admin_database_page import render_admin_database_page
from frontend.admin_users_page import render_admin_users_page
from frontend.admin_feedback_page import render_admin_feedback_page
from frontend.admin_notifications_page import render_admin_notifications_page
from frontend.admin_broadcast_page import render_admin_broadcast_page

ADMIN_NAV_OPTIONS = ["Dashboard", "Database", "Users", "Feedback", "Announcements", "Notifications"]
ADMIN_NAV_ICONS = ["speedometer2", "database", "people", "chat-left-text", "megaphone", "bell"]

ADMIN_ROUTES = {
    "Dashboard": render_admin_dashboard_page,
    "Database": render_admin_database_page,
    "Users": render_admin_users_page,
    "Feedback": render_admin_feedback_page,
    "Announcements": render_admin_notifications_page,
    "Notifications": render_admin_broadcast_page,
}


def render_admin_panel() -> None:
    """Entry point: renders the Admin Login page if no admin session
    exists yet, otherwise the full Admin Panel with sidebar routing."""
    st.session_state.setdefault("admin_user", None)
    st.session_state.setdefault("admin_page", "Dashboard")

    if st.session_state["admin_user"] is None:
        render_admin_login_page()
        return

    admin = st.session_state["admin_user"]

    with st.sidebar:
        st.markdown(
            f"<h3 class='pathway-display' style='margin-bottom:0;'>🛡️ Admin Panel</h3>"
            f"<p class='muted' style='margin-top:2px;'>{admin.get('first_name', '')} {admin.get('last_name', '')}</p>",
            unsafe_allow_html=True,
        )
        st.markdown("---")

        if st.session_state["admin_page"] not in ADMIN_NAV_OPTIONS:
            st.session_state["admin_page"] = "Dashboard"

        selected = option_menu(
            menu_title=None,
            options=ADMIN_NAV_OPTIONS,
            icons=ADMIN_NAV_ICONS,
            default_index=ADMIN_NAV_OPTIONS.index(st.session_state["admin_page"]),
            key="admin_panel_nav",
            styles={
                "container": {"padding": "0", "background-color": "transparent"},
                "icon": {"color": "#7C5CFF", "font-size": "16px"},
                "nav-link": {"font-size": "14px", "text-align": "left", "margin": "2px 0", "border-radius": "10px"},
                "nav-link-selected": {"background": "linear-gradient(120deg, #7C5CFF, #22D3B0)", "color": "white"},
            },
        )
        if selected != st.session_state["admin_page"]:
            st.session_state["admin_page"] = selected
            st.rerun()

        st.markdown("---")
        if st.button("🚪 Exit Admin Panel", key="admin_panel_logout", use_container_width=True):
            st.session_state["admin_user"] = None
            st.session_state["admin_page"] = "Dashboard"
            st.rerun()

    st.markdown("<div class='hero-eyebrow'>🛡️ Admin Panel</div>", unsafe_allow_html=True)
    ADMIN_ROUTES[st.session_state["admin_page"]]()
