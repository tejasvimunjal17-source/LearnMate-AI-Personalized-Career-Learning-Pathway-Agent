"""
frontend/feedback_page.py
-----------------------------
User-facing feedback module: lets a logged-in user rate the platform and
submit general feedback, bug reports, or feature requests — all stored
in Supabase's `feedback` table via backend.feedback_store.submit_feedback().

This is a regular user page, not part of the Admin Panel. It shares no
code with frontend/admin_feedback_page.py (which only reads and manages
existing feedback) - this page only writes.
"""

from __future__ import annotations

import streamlit as st

from backend.feedback_store import submit_feedback, FeedbackStoreError
from backend.activity_logger import log_activity
from frontend.components import hero, glass_card_open, glass_card_close

CATEGORY_LABELS = {
    "general": "💬 General Feedback",
    "bug": "🐞 Bug Report",
    "feature": "✨ Feature Request",
}


def render_feedback_page() -> None:
    user = st.session_state.get("auth_user")
    if not user:
        st.warning("You need to register or log in first.")
        return

    hero(
        "We'd Love Your Input",
        "💬 Feedback & Suggestions",
        "Rate LearnMate AI, report a bug, or suggest a feature — it goes straight to our team.",
    )

    glass_card_open("Share Your Thoughts")
    with st.form("user_feedback_form", clear_on_submit=True):
        category_label = st.radio(
            "What kind of feedback is this?",
            options=list(CATEGORY_LABELS.values()),
            horizontal=True,
        )
        category = next(k for k, v in CATEGORY_LABELS.items() if v == category_label)

        rating = st.slider(
            "⭐ Rate the platform (optional)",
            min_value=0, max_value=5, value=0,
            help="0 = skip rating",
        )

        message = st.text_area(
            "Your message",
            placeholder={
                "general": "What's working well? What could be better?",
                "bug": "What happened? What did you expect instead? Steps to reproduce, if you have them.",
                "feature": "What would you like to see added or changed?",
            }.get(category, ""),
            height=150,
        )

        submitted = st.form_submit_button("📤 Submit", use_container_width=True)

    glass_card_close()

    if submitted:
        try:
            submit_feedback(
                email=user["email"],
                message=message,
                category=category,
                rating=rating if rating > 0 else None,
            )
        except FeedbackStoreError as exc:
            st.error(str(exc))
        else:
            log_activity(user["email"], "feedback_submission", detail={"category": category})
            st.success("✅ Thank you! Your feedback has been submitted.")
