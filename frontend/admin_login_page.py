"""
frontend/admin_login_page.py
--------------------------------
Dedicated Admin Login screen, kept completely separate from
frontend/auth_page.py (the regular passwordless user login).

Admins authenticate with email + bcrypt-verified password against the
`admin_users` table via backend.admin_auth.verify_admin_login(). A
successful login is stored under st.session_state["admin_user"] — a
distinct key from the regular st.session_state["auth_user"] — so an
admin session never overlaps with, reads from, or writes to a normal
user's session state. Logging in as an admin does not log a user out,
and vice versa.
"""

from __future__ import annotations

import streamlit as st

from backend.admin_auth import verify_admin_login, AdminAuthError
from backend.activity_logger import log_admin_login, log_admin_activity
from frontend.components import hero, glass_card_open, glass_card_close


def render_admin_login_page() -> None:
    """Render the Admin Login form. On success, sets
    st.session_state["admin_user"] and reruns the app."""
    hero(
        "Admin Panel",
        "🛡️ LearnMate AI — Admin Login",
        "Restricted access. Sign in with your administrator credentials.",
    )

    glass_card_open()
    with st.form("admin_login_form", clear_on_submit=False):
        email = st.text_input("Admin Email", placeholder="admin@learnmate.ai")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("🔐 Sign In", use_container_width=True)
    glass_card_close()

    if submitted:
        admin = None
        try:
            admin = verify_admin_login(email, password)
        except AdminAuthError as exc:
            st.error(str(exc))
        except Exception as exc:  # noqa: BLE001 - never let an unexpected error strand the user here
            st.error(f"Something went wrong: {exc}")

        if admin is not None:
            st.session_state["admin_user"] = {
                "id": admin.id,
                "email": admin.email,
                "first_name": admin.first_name,
                "last_name": admin.last_name,
                "is_super_admin": admin.is_super_admin,
            }
            st.session_state["admin_page"] = "Dashboard"
            st.session_state["admin_login_log_id"] = log_admin_login(admin.id)
            log_admin_activity(admin.id, "admin_login")
            st.success(f"✅ Welcome back, {admin.first_name}.")
            st.rerun()

    st.markdown("---")
    if st.button("← Back to LearnMate AI", key="admin_login_back"):
        st.session_state["force_admin_mode"] = False
        st.query_params.clear()
        st.rerun()
