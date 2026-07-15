"""
frontend/landing.py
----------------------
The public "Home" page shown before a visitor registers/logs in — a premium
SaaS-style landing page with a fixed top navigation bar, animated gradient
hero, features grid, stats cards, and footer.
"""

from __future__ import annotations

import streamlit as st


def render_topnav(authenticated: bool) -> None:
    """Fixed top navigation bar. Real navigation happens via the buttons
    rendered just under it (Streamlit can't put interactive widgets inside
    raw HTML), which this bar visually anchors to."""
    links = "🏠 Home &nbsp;·&nbsp; 👤 My Profile &nbsp;·&nbsp; 📊 Dashboard" if authenticated else "🏠 Home"
    st.markdown(
        f"""
        <div class="lm-topnav">
            <div class="lm-topnav-brand">🧭 LearnMate <span class="lm-topnav-ai">AI</span></div>
            <div class="lm-topnav-links">{links}</div>
        </div>
        <div style="height:64px;"></div>
        """,
        unsafe_allow_html=True,
    )


def render_landing_page() -> None:
    st.markdown(
        """
        <div class="lm-hero">
            <div class="lm-hero-badge">✨ Powered by IBM watsonx.ai &middot; Granite Foundation Models</div>
            <h1 class="lm-hero-title">Your AI-Powered<br/>Career Learning Pathway</h1>
            <p class="lm-hero-sub">
                LearnMate AI designs a fully personalized roadmap, closes your skill gaps,
                and recommends real courses &amp; certifications — so you always know exactly
                what to learn next.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        b1, b2 = st.columns(2)
        get_started = b1.button("🚀 Get Started", use_container_width=True, key="landing_get_started")
        talk_ai = b2.button("💬 Talk to AI Mentor", use_container_width=True, key="landing_talk_ai")

    st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)

    # ---- Features ----
    st.markdown("<h2 class='lm-section-title'>Everything you need to reach your goal</h2>", unsafe_allow_html=True)
    features = [
        ("🧠", "AI-Generated Roadmap", "A week-by-week plan tailored to your goal, level, and pace, built by IBM Granite models."),
        ("📊", "Skill Gap Analysis", "See exactly which skills to prioritize with an interactive readiness gauge."),
        ("🎓", "Curated Courses & Certs", "Official links to IBM, Coursera, Google, Microsoft, AWS and more — no guesswork."),
        ("💬", "AI Mentor Chatbot", "A floating assistant ready to answer questions about your roadmap, anytime."),
        ("📈", "Live Dashboard", "Track completion %, study hours, and certifications earned in one place."),
        ("📥", "Downloadable Reports", "Export your full profile, roadmap and progress as a polished PDF or Word doc."),
    ]
    cols = st.columns(3)
    for i, (icon, title, desc) in enumerate(features):
        with cols[i % 3]:
            st.markdown(
                f"""
                <div class="glass-card lm-feature-card">
                    <div class="lm-feature-icon">{icon}</div>
                    <div class="lm-feature-title">{title}</div>
                    <div class="muted lm-feature-desc">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ---- Stats ----
    st.markdown("<h2 class='lm-section-title'>Trusted learning, built on real platforms</h2>", unsafe_allow_html=True)
    scols = st.columns(4)
    stats = [
        ("10+", "Career Domains"),
        ("50+", "Official Courses & Certs"),
        ("15+", "Learning Platforms"),
        ("100%", "Free to Get Started"),
    ]
    for col, (value, label) in zip(scols, stats):
        with col:
            st.markdown(
                f"""
                <div class="metric-card" style="text-align:center;">
                    <div class="metric-value">{value}</div>
                    <div class="metric-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)

    # ---- Footer ----
    st.markdown(
        """
        <div class="lm-footer">
            <div>🧭 <strong>LearnMate AI</strong> — an AI Career Learning Platform</div>
            <div class="muted" style="font-size:0.8rem; margin-top:6px;">
                Powered by IBM watsonx.ai (Granite) &middot; IBM watsonx Orchestrate &middot; Google Sheets
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if get_started:
        st.session_state["landing_view"] = "register"
        st.rerun()
    if talk_ai:
        st.session_state["chatbot_open"] = True
        st.rerun()
