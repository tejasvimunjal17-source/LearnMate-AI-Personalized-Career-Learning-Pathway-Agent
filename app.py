"""
app.py
--------
LearnMate AI - AI Career Learning Platform - main Streamlit entrypoint.

Run locally:
    streamlit run app.py

See README.md for full setup, environment configuration, and deployment
instructions (Streamlit Community Cloud + GitHub + Google Sheets + IBM
watsonx.ai / watsonx Orchestrate).
"""

from __future__ import annotations

import streamlit as st
from streamlit_option_menu import option_menu

from config import CONFIG, SHEETS_CONFIG
from agent_instructions import DOMAIN_SPECIALIZATION
from backend.logger_setup import get_logger
from backend.roadmap_engine import StudentProfile, generate_roadmap
from backend.skill_gap import normalize_skill_gaps, overall_readiness_percent
from backend.pdf_report import build_pdf_report
from backend.docx_report import build_docx_report
from backend.recommendations import get_courses_for_domain, get_certifications_for_domain
from backend.responses_store import save_response
from utils.validators import validate_profile

from frontend.styles import inject_css
from frontend.landing import render_landing_page, render_topnav
from frontend.auth_page import render_auth_page
from frontend.profile_page import render_profile_page
from frontend.chatbot import render_chatbot_widget
from frontend.components import (
    hero, metric_card, glass_card_open, glass_card_close, progress_bar,
    milestone_node, skill_gap_row, empty_state, course_card, cert_card,
)
from frontend.charts import readiness_gauge, skill_gap_bar, weekly_effort_line, progress_donut

logger = get_logger(__name__)

DOMAINS = sorted(DOMAIN_SPECIALIZATION.keys())
LEVELS = ["Beginner", "Intermediate", "Advanced"]
LEARNING_STYLES = ["Video Lectures", "Reading / Docs", "Hands-on Projects", "Mixed / Balanced"]

# ----------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="LearnMate AI | Career Learning Platform",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------
# Session state defaults
# ----------------------------------------------------------------------
DEFAULTS = {
    "dark_mode": True,
    "profile": None,
    "roadmap": None,
    "completed_weeks": set(),
    "completed_courses": set(),
    "completed_certs": set(),
    "page": "Career Profile",
    "auth_user": None,          # {first_name, last_name, email, registration_date}
    "landing_view": "home",     # "home" | "register" | "app"
    "chatbot_open": False,
    "chat_history": [],
}
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)

inject_css(dark_mode=st.session_state["dark_mode"])

AUTHENTICATED = st.session_state["auth_user"] is not None

# The AI Mentor chatbot floats on every screen, logged in or not.
render_chatbot_widget()


# ========================================================================
# UNAUTHENTICATED FLOW: Landing page -> Registration/Login
# ========================================================================
if not AUTHENTICATED:
    render_topnav(authenticated=False)

    if st.session_state["landing_view"] == "register":
        render_auth_page()
    else:
        render_landing_page()

    st.stop()


# ========================================================================
# AUTHENTICATED APP
# ========================================================================
render_topnav(authenticated=True)

with st.sidebar:
    user = st.session_state["auth_user"]
    st.markdown(
        f"<h2 class='pathway-display' style='margin-bottom:0;'>🧭 LearnMate AI</h2>"
        f"<p class='muted' style='margin-top:2px;'>Hi, {user['first_name']} 👋</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    NAV_OPTIONS = ["Home", "My Profile", "Career Profile", "AI Roadmap", "Skill Gap",
                   "Courses & Certs", "Progress Tracker", "Dashboard"]
    NAV_ICONS = ["house", "person-badge", "person-lines-fill", "signpost-split",
                 "bar-chart-steps", "mortarboard", "check2-square", "grid-1x2"]

    if st.session_state["page"] not in NAV_OPTIONS:
        st.session_state["page"] = "Career Profile"

    page = option_menu(
        menu_title=None,
        options=NAV_OPTIONS,
        icons=NAV_ICONS,
        default_index=NAV_OPTIONS.index(st.session_state["page"]),
        styles={
            "container": {"padding": "0", "background-color": "transparent"},
            "icon": {"color": "#7C5CFF", "font-size": "16px"},
            "nav-link": {"font-size": "14px", "text-align": "left", "margin": "2px 0", "border-radius": "10px"},
            "nav-link-selected": {"background": "linear-gradient(120deg, #7C5CFF, #22D3B0)", "color": "white"},
        },
    )
    st.session_state["page"] = page

    st.markdown("---")
    dark = st.toggle("🌙 Dark Mode", value=st.session_state["dark_mode"])
    if dark != st.session_state["dark_mode"]:
        st.session_state["dark_mode"] = dark
        st.rerun()

    st.markdown("---")
    status_ok = CONFIG.is_configured
    status_label = "🟢 watsonx.ai configured" if status_ok else "🟡 Offline demo mode"
    st.caption(status_label)
    if not status_ok:
        st.caption(
            "Add WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL and "
            "WATSONX_MODEL_ID to your .env to enable live AI generation."
        )
    sheets_label = "🟢 Google Sheets connected" if SHEETS_CONFIG.is_configured else "🟡 Local storage fallback"
    st.caption(sheets_label)

    if st.button("🚪 Logout", key="sidebar_logout", use_container_width=True):
        for k in ["auth_user", "profile", "roadmap", "completed_weeks", "completed_courses", "completed_certs"]:
            st.session_state[k] = DEFAULTS[k] if k in DEFAULTS else None
        st.session_state["landing_view"] = "home"
        st.session_state["page"] = "Career Profile"
        st.rerun()


# ----------------------------------------------------------------------
# PAGE: Home (post-login shortcut back to the landing content)
# ----------------------------------------------------------------------
def render_home_page() -> None:
    render_landing_page()


# ----------------------------------------------------------------------
# PAGE: Career Profile (the AI Roadmap intake form)
# ----------------------------------------------------------------------
def render_profile_form_page() -> None:
    hero(
        "Step 2 of 2",
        "Tell us about you",
        "Your AI Career Mentor uses this profile to design a roadmap tailored "
        "exactly to your goal, pace, and starting point.",
    )

    with st.form("profile_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input(
                "Full Name *",
                value=f"{st.session_state['auth_user']['first_name']} {st.session_state['auth_user']['last_name']}",
            )
            career_goal = st.text_input(
                "Career Goal *", placeholder="e.g. Become a Machine Learning Engineer"
            )
            current_level = st.selectbox("Current Level *", LEVELS)
            study_hours = st.number_input(
                "Study Hours per Week *", min_value=1, max_value=100, value=10, step=1
            )
        with c2:
            preferred_domain = st.selectbox("Preferred Domain *", DOMAINS)
            learning_preference = st.selectbox("Preferred Learning Style *", LEARNING_STYLES)
            existing_skills_raw = st.text_area(
                "Existing Skills (comma-separated)",
                placeholder="e.g. Python, Excel, HTML, SQL",
                height=100,
            )

        submitted = st.form_submit_button("🚀 Generate My Roadmap", use_container_width=True)

    if submitted:
        existing_skills = [s.strip() for s in existing_skills_raw.split(",") if s.strip()]
        errors = validate_profile(
            name, career_goal, current_level, study_hours,
            preferred_domain, learning_preference, existing_skills,
        )
        if errors:
            for e in errors:
                st.error(e)
            return

        profile = StudentProfile(
            name=name.strip(),
            career_goal=career_goal.strip(),
            current_level=current_level,
            study_hours_per_week=int(study_hours),
            preferred_domain=preferred_domain,
            learning_preference=learning_preference,
            existing_skills=existing_skills,
        )
        st.session_state["profile"] = profile

        with st.spinner("🧠 Your AI Career Mentor is designing your roadmap..."):
            try:
                roadmap = generate_roadmap(profile)
                st.session_state["roadmap"] = roadmap
                st.session_state["completed_weeks"] = set()
                logger.info("Roadmap successfully generated for %s", profile.name)
            except Exception as exc:  # noqa: BLE001 - surfaced to user safely
                logger.exception("Unexpected error generating roadmap")
                st.error(f"Something went wrong while generating your roadmap: {exc}")
                return

        save_response(st.session_state["auth_user"]["email"], profile)

        st.success(f"✅ Roadmap generated for **{profile.name}**! Open **AI Roadmap** from the sidebar.")
        st.balloons()


# ----------------------------------------------------------------------
# PAGE: AI Roadmap
# ----------------------------------------------------------------------
def render_roadmap_page() -> None:
    profile: StudentProfile | None = st.session_state["profile"]
    roadmap = st.session_state["roadmap"]

    if not profile or not roadmap:
        empty_state("🧭", "No roadmap yet. Fill out your **Career Profile** first to generate a personalized pathway.")
        return

    domain_display = profile.preferred_domain.title()
    hero(
        "AI-Generated Pathway",
        f"{profile.name}'s Roadmap to {profile.career_goal}",
        f"Domain: **{domain_display}** &bull; Level: {profile.current_level} &bull; "
        f"{profile.study_hours_per_week} hrs/week &bull; "
        f"~{roadmap.get('estimated_duration_weeks', '-')} weeks",
    )

    if roadmap.get("_source", "").startswith("offline"):
        st.warning(
            "⚠️ Shown in **offline demo mode** because watsonx.ai wasn't reachable "
            f"({roadmap.get('_fallback_reason', 'not configured')}). "
            "Configure your `.env` for fully AI-personalized roadmaps."
        )

    glass_card_open("📋 Overview")
    st.write(roadmap.get("summary", ""))
    glass_card_close()

    st.markdown("### 🛤️ Weekly Milestones")
    for m in roadmap.get("weekly_milestones", []):
        glass_card_open()
        milestone_node(m)
        glass_card_close()

    if roadmap.get("capstone_project"):
        glass_card_open("🏆 Capstone Project")
        st.write(roadmap["capstone_project"])
        glass_card_close()

    # ---- Export ----
    st.markdown("### 📥 Export")
    profile_dict = {
        "name": profile.name,
        "career_goal": profile.career_goal,
        "current_level": profile.current_level,
        "study_hours_per_week": profile.study_hours_per_week,
        "preferred_domain": domain_display,
        "learning_preference": profile.learning_preference,
        "existing_skills": profile.existing_skills,
    }
    readiness = overall_readiness_percent(roadmap.get("skill_gap_analysis", []))

    ec1, ec2 = st.columns(2)
    with ec1:
        try:
            pdf_bytes = build_pdf_report(profile=profile_dict, roadmap=roadmap)
            st.download_button(
                "⬇️ Download as PDF",
                data=pdf_bytes,
                file_name=f"{profile.name.replace(' ', '_')}_career_roadmap.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception:
            logger.exception("PDF generation failed")
            st.error("Couldn't generate the PDF report right now.")
    with ec2:
        try:
            docx_bytes = build_docx_report(
                profile=profile_dict, roadmap=roadmap,
                completed_weeks=len(st.session_state["completed_weeks"]),
                readiness_percent=readiness,
            )
            st.download_button(
                "⬇️ Download as Word (.docx)",
                data=docx_bytes,
                file_name=f"{profile.name.replace(' ', '_')}_career_report.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        except Exception:
            logger.exception("DOCX generation failed")
            st.error("Couldn't generate the Word report right now.")


# ----------------------------------------------------------------------
# PAGE: Skill Gap
# ----------------------------------------------------------------------
def render_skill_gap_page() -> None:
    roadmap = st.session_state["roadmap"]
    profile = st.session_state["profile"]
    if not roadmap:
        empty_state("📊", "Generate your roadmap first to see your skill-gap analysis.")
        return

    domain_display = profile.preferred_domain.title() if profile else ""
    hero("Skill Gap Analysis", f"Where You Stand in {domain_display}",
         "A side-by-side look at your current skill levels vs. what your target role requires.")

    gaps = normalize_skill_gaps(roadmap.get("skill_gap_analysis", []))
    if not gaps:
        empty_state("✅", "No skill gaps identified yet.")
        return

    readiness = overall_readiness_percent(roadmap.get("skill_gap_analysis", []))
    c1, c2 = st.columns([1, 2])
    with c1:
        st.plotly_chart(readiness_gauge(readiness, st.session_state["dark_mode"]), use_container_width=True)
    with c2:
        st.plotly_chart(skill_gap_bar(gaps, st.session_state["dark_mode"]), use_container_width=True)

    glass_card_open("Detailed Breakdown")
    hc1, hc2, hc3, hc4 = st.columns([3, 2, 2, 1.4])
    hc1.markdown("**Skill**")
    hc2.markdown("**Current**")
    hc3.markdown("**Required**")
    hc4.markdown("**Priority**")
    st.markdown("<hr style='margin:4px 0; opacity:0.15;'>", unsafe_allow_html=True)
    for g in gaps:
        skill_gap_row(g)
    glass_card_close()


# ----------------------------------------------------------------------
# PAGE: Courses & Certifications
# ----------------------------------------------------------------------
def render_courses_page() -> None:
    profile = st.session_state["profile"]
    if not profile:
        empty_state("🎓", "Generate your roadmap first to see course & certification recommendations.")
        return

    hero("Course Recommendation Dashboard", "Courses & Certifications",
         f"Official, curated learning resources for **{profile.preferred_domain}** — "
         "check items off as you complete them to update your Dashboard.")

    st.markdown("### 📚 Recommended Courses")
    courses = get_courses_for_domain(profile.preferred_domain)
    cols = st.columns(3)
    for i, c in enumerate(courses):
        with cols[i % 3]:
            course_card(c)
            done = st.checkbox("Mark completed", key=f"course_done_{i}", value=c.name in st.session_state["completed_courses"])
            if done:
                st.session_state["completed_courses"].add(c.name)
            else:
                st.session_state["completed_courses"].discard(c.name)

    st.markdown("### 🏅 Recommended Certifications")
    certs = get_certifications_for_domain(profile.preferred_domain)
    ccols = st.columns(3)
    for i, cert in enumerate(certs):
        with ccols[i % 3]:
            cert_card(cert)
            earned = st.checkbox("Mark earned", key=f"cert_done_{i}", value=cert.name in st.session_state["completed_certs"])
            if earned:
                st.session_state["completed_certs"].add(cert.name)
            else:
                st.session_state["completed_certs"].discard(cert.name)


# ----------------------------------------------------------------------
# PAGE: Progress Tracker
# ----------------------------------------------------------------------
def render_progress_page() -> None:
    roadmap = st.session_state["roadmap"]
    profile = st.session_state["profile"]
    if not roadmap:
        empty_state("✅", "Generate your roadmap first to start tracking progress.")
        return

    hero("Progress Tracker", f"{profile.name}'s Journey" if profile else "Your Journey",
         "Check off each week as you complete it - your dashboard updates automatically.")

    milestones = roadmap.get("weekly_milestones", [])
    total = len(milestones)
    completed = st.session_state["completed_weeks"]

    progress_bar(round((len(completed) / total) * 100) if total else 0, "Overall Roadmap Progress")
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    for m in milestones:
        week = m.get("week")
        checked = week in completed
        new_val = st.checkbox(
            f"Week {week}: {m.get('title', '')}", value=checked, key=f"week_check_{week}"
        )
        if new_val and week not in completed:
            completed.add(week)
        elif not new_val and week in completed:
            completed.discard(week)

    st.session_state["completed_weeks"] = completed


# ----------------------------------------------------------------------
# PAGE: Dashboard
# ----------------------------------------------------------------------
def render_dashboard_page() -> None:
    roadmap = st.session_state["roadmap"]
    profile = st.session_state["profile"]
    if not roadmap or not profile:
        empty_state("📈", "Generate your roadmap first to unlock your interactive dashboard.")
        return

    domain_display = profile.preferred_domain.title()
    hero("Interactive Dashboard", f"{domain_display} Career Overview",
         f"A bird's-eye view of {profile.name}'s roadmap, pace, and readiness.")

    milestones = roadmap.get("weekly_milestones", [])
    total_weeks = roadmap.get("estimated_duration_weeks", len(milestones) or 1)
    completed = len(st.session_state["completed_weeks"])
    readiness = overall_readiness_percent(roadmap.get("skill_gap_analysis", []))
    total_hours = total_weeks * profile.study_hours_per_week
    completion_pct = round((completed / len(milestones)) * 100) if milestones else 0

    m1, m2, m3, m4 = st.columns(4)
    metric_card("Roadmap Progress", f"{completion_pct}%", m1)
    metric_card("Skill Readiness", f"{readiness}%", m2)
    metric_card("Study Hours", f"{total_hours} hrs", m3)
    metric_card("Weekly Progress", f"{completed}/{len(milestones)} wks", m4)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    m5, m6 = st.columns(2)
    metric_card("Certifications Earned", str(len(st.session_state["completed_certs"])), m5)
    metric_card("Courses Completed", str(len(st.session_state["completed_courses"])), m6)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(progress_donut(completed, len(milestones), st.session_state["dark_mode"]), use_container_width=True)
    with c2:
        st.plotly_chart(readiness_gauge(readiness, st.session_state["dark_mode"]), use_container_width=True)

    st.plotly_chart(
        weekly_effort_line(total_weeks, profile.study_hours_per_week, st.session_state["dark_mode"]),
        use_container_width=True,
    )

    gaps = normalize_skill_gaps(roadmap.get("skill_gap_analysis", []))
    if gaps:
        st.plotly_chart(skill_gap_bar(gaps, st.session_state["dark_mode"]), use_container_width=True)


# ----------------------------------------------------------------------
# Router
# ----------------------------------------------------------------------
PAGES = {
    "Home": render_home_page,
    "My Profile": render_profile_page,
    "Career Profile": render_profile_form_page,
    "AI Roadmap": render_roadmap_page,
    "Skill Gap": render_skill_gap_page,
    "Courses & Certs": render_courses_page,
    "Progress Tracker": render_progress_page,
    "Dashboard": render_dashboard_page,
}

try:
    PAGES[st.session_state["page"]]()
except Exception as exc:  # noqa: BLE001 - top-level safety net
    logger.exception("Unhandled error rendering page '%s'", st.session_state["page"])
    st.error(f"An unexpected error occurred: {exc}")
    st.caption("Please refresh the page or check the logs for more details.")
