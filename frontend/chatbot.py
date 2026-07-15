"""
frontend/chatbot.py
----------------------
Floating "AI Mentor" chat assistant, rendered in the bottom-right corner on
every page (minimize/maximize, welcome message, suggested questions, chat
history, responsive).

This widget reserves the integration point for **IBM watsonx Orchestrate**:
if WATSONX_ORCHESTRATE_EMBED_URL is set, the panel embeds the real
Orchestrate agent via iframe. Until that's configured, it falls back to a
lightweight rule-based responder grounded in the student's own roadmap data
so the widget is fully functional out of the box.
"""

from __future__ import annotations

import streamlit as st

from config import ORCHESTRATE_CONFIG

SUGGESTED_QUESTIONS = [
    "What should I focus on this week?",
    "How do I close my biggest skill gap?",
    "Recommend a certification for my domain.",
    "How many hours until I finish my roadmap?",
]


def _rule_based_reply(question: str) -> str:
    q = question.lower()
    roadmap = st.session_state.get("roadmap")
    profile = st.session_state.get("profile")

    if not roadmap or not profile:
        return (
            "I don't see a roadmap yet — head to **AI Roadmap** and fill out your "
            "profile first, then I can give you specific guidance!"
        )

    if "week" in q or "focus" in q:
        milestones = roadmap.get("weekly_milestones", [])
        completed = st.session_state.get("completed_weeks", set())
        next_week = next((m for m in milestones if m.get("week") not in completed), None)
        if next_week:
            return f"Right now, focus on **Week {next_week.get('week')}: {next_week.get('title')}**."
        return "Looks like you've completed every milestone — great work! Consider a capstone project next."

    if "gap" in q or "skill" in q:
        gaps = roadmap.get("skill_gap_analysis", [])
        high = [g for g in gaps if g.get("priority") == "High"]
        if high:
            names = ", ".join(g.get("skill", "") for g in high[:3])
            return f"Your highest-priority skill gaps are: **{names}**. Tackle those first."
        return "No high-priority gaps detected — you're in good shape!"

    if "cert" in q:
        return (
            f"Check the **Courses & Certs** page for certifications curated for "
            f"**{profile.preferred_domain}**, with official links."
        )

    if "hour" in q or "time" in q or "finish" in q:
        total_weeks = roadmap.get("estimated_duration_weeks", len(roadmap.get("weekly_milestones", [])))
        hours = total_weeks * profile.study_hours_per_week
        return f"At {profile.study_hours_per_week} hrs/week, your roadmap totals about **{hours} hours** over {total_weeks} weeks."

    return (
        "I'm your AI Career Mentor! Ask me about your weekly focus, skill gaps, "
        "certifications, or timeline — or connect IBM watsonx Orchestrate for "
        "fully open-ended conversations."
    )


def render_chatbot_widget() -> None:
    st.session_state.setdefault("chatbot_open", False)
    st.session_state.setdefault("chat_history", [])

    # Floating launcher + panel, pinned bottom-right via the "lm_chatbot"
    # container key (Streamlit auto-assigns a `.st-key-lm_chatbot` class,
    # which frontend/styles.py targets with position:fixed). z-index and a
    # bottom-margin keep it from ever overlapping the main UI.
    with st.container(key="lm_chatbot"):
        toggle_label = "✖️ Close AI Mentor" if st.session_state["chatbot_open"] else "💬 AI Mentor"
        if st.button(toggle_label, key="chat_toggle_btn"):
            st.session_state["chatbot_open"] = not st.session_state["chatbot_open"]
            st.rerun()

        if st.session_state["chatbot_open"]:
            st.markdown("#### 🧭 AI Career Mentor")

            if ORCHESTRATE_CONFIG.is_configured:
                st.caption("🟢 Connected to IBM watsonx Orchestrate")
                st.markdown(
                    f'<iframe src="{ORCHESTRATE_CONFIG.embed_url}" '
                    'style="width:100%;height:360px;border:none;border-radius:12px;"></iframe>',
                    unsafe_allow_html=True,
                )
            else:
                st.caption("🟡 Demo mentor — connect watsonx Orchestrate for full conversations")
                if not st.session_state["chat_history"]:
                    st.info("👋 Hi! I'm your AI Career Mentor. Ask me anything about your roadmap.")

                st.markdown("**Suggested questions:**")
                for i, sq in enumerate(SUGGESTED_QUESTIONS):
                    if st.button(sq, key=f"suggest_q_{i}", use_container_width=True):
                        reply = _rule_based_reply(sq)
                        st.session_state["chat_history"].append((sq, reply))
                        st.rerun()

                for q, a in st.session_state["chat_history"][-6:]:
                    st.markdown(f"**You:** {q}")
                    st.markdown(f"**Mentor:** {a}")

                user_q = st.text_input("Type a question...", key="chat_input")
                if st.button("Send", key="chat_send_btn") and user_q.strip():
                    reply = _rule_based_reply(user_q)
                    st.session_state["chat_history"].append((user_q, reply))
                    st.rerun()
