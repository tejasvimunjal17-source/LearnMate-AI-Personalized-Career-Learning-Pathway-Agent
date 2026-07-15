"""
frontend/auth_page.py
------------------------
Registration ("create your account") and returning-user login screens,
rendered before a visitor can reach the roadmap generator, dashboard, or
profile page. Registrations are persisted via backend.auth into the
"LearnMate AI Users Data" Google Sheet (local CSV fallback if not configured).
"""

from __future__ import annotations

import streamlit as st

from backend.auth import register_user, login_existing_user, RegistrationError
from frontend.components import hero, glass_card_open, glass_card_close


def render_auth_page() -> None:
    hero(
        "Step 1 of 2",
        "Create your LearnMate AI account",
        "Just three quick details — we'll remember you so you never have to register twice.",
    )

    tab_register, tab_login = st.tabs(["🆕 Register", "🔑 Continue with existing email"])

    with tab_register:
        glass_card_open()
        with st.form("register_form", clear_on_submit=False):
            c1, c2 = st.columns(2)
            first_name = c1.text_input("First Name *", placeholder="e.g. Aisha")
            last_name = c2.text_input("Last Name *", placeholder="e.g. Khan")
            email = st.text_input("Email Address *", placeholder="e.g. aisha@example.com")
            submitted = st.form_submit_button("🚀 Register & Continue", use_container_width=True)
        glass_card_close()

        if submitted:
            try:
                user = register_user(first_name, last_name, email)
                st.session_state["auth_user"] = user.to_dict()
                st.session_state["landing_view"] = "app"
                st.success(f"✅ Welcome, {user.first_name}! Redirecting to your AI Roadmap form...")
                st.rerun()
            except RegistrationError as exc:
                st.error(str(exc))

    with tab_login:
        glass_card_open()
        with st.form("login_form", clear_on_submit=False):
            login_email = st.text_input("Registered Email Address", placeholder="e.g. aisha@example.com")
            login_submitted = st.form_submit_button("🔑 Continue", use_container_width=True)
        glass_card_close()

        if login_submitted:
            try:
                user = login_existing_user(login_email)
                st.session_state["auth_user"] = user.to_dict()
                st.session_state["landing_view"] = "app"
                st.success(f"✅ Welcome back, {user.first_name}!")
                st.rerun()
            except RegistrationError as exc:
                st.error(str(exc))

    if st.button("← Back to Home", key="auth_back_home"):
        st.session_state["landing_view"] = "home"
        st.rerun()
