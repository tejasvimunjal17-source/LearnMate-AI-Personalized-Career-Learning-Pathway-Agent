"""
frontend/profile_page.py
---------------------------
"My Profile" account page: shows the logged-in user's First Name, Last Name,
Email, and Registration Date, with Edit Profile / Logout actions.
"""

from __future__ import annotations

import streamlit as st

from backend.auth import update_user_name, RegistrationError
from frontend.components import hero, glass_card_open, glass_card_close, metric_card


def render_profile_page() -> None:
    user = st.session_state.get("auth_user")
    if not user:
        st.warning("You need to register or log in first.")
        return

    hero("My Profile", f"{user['first_name']} {user['last_name']}", "Your LearnMate AI account details.")

    c1, c2, c3 = st.columns(3)
    metric_card("Email", user["email"], c1)
    metric_card("Registered On", user.get("registration_date", "-"), c2)
    metric_card("Roadmap Status", "Generated ✅" if st.session_state.get("roadmap") else "Not started", c3)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    glass_card_open("✏️ Edit Profile")
    with st.form("edit_profile_form"):
        c1, c2 = st.columns(2)
        new_first = c1.text_input("First Name", value=user["first_name"])
        new_last = c2.text_input("Last Name", value=user["last_name"])
        st.text_input("Email Address", value=user["email"], disabled=True, help="Email can't be changed — it's your account identifier.")
        save = st.form_submit_button("💾 Save Changes", use_container_width=True)
    glass_card_close()

    if save:
        try:
            update_user_name(user["email"], new_first, new_last)
            st.session_state["auth_user"]["first_name"] = new_first.strip()
            st.session_state["auth_user"]["last_name"] = new_last.strip()
            st.success("✅ Profile updated.")
            st.rerun()
        except RegistrationError as exc:
            st.error(str(exc))

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    if st.button("🚪 Logout", key="profile_logout", use_container_width=True):
        for key in ["auth_user", "profile", "roadmap", "completed_weeks"]:
            st.session_state.pop(key, None)
        st.session_state["landing_view"] = "home"
        st.session_state["page"] = "Career Profile"
        st.rerun()
