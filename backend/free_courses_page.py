"""
frontend/free_courses_page.py
-------------------------------
Renders the "Free Courses" page: search + filter over the curated
catalogue in backend/free_courses.py, using the same hero/glass-card
visual language as the rest of LearnMate AI.
"""

from __future__ import annotations

import streamlit as st

from backend.free_courses import (
    DOMAINS,
    PLATFORMS,
    DIFFICULTIES,
    DURATIONS,
    FreeCourse,
    search_free_courses,
)
from frontend.components import hero, glass_card_open, glass_card_close, empty_state


def _render_course_card(course: FreeCourse) -> None:
    glass_card_open(course.name)
    st.caption(f"🏫 {course.provider}  ·  🌐 {course.platform}")

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"**Difficulty**\n\n{course.difficulty}")
    c2.markdown(f"**Duration**\n\n{course.duration}")
    c3.markdown(f"**Certificate**\n\n{'✅ Yes' if course.certificate else '➖ No'}")

    st.link_button("🚀 Enroll (Official Page)", course.url, use_container_width=True)
    glass_card_close()


def render_free_courses_page() -> None:
    hero(
        "Free Learning Catalogue",
        "📚 Free Courses",
        "Curated free courses from official platforms - Google Skillshop, "
        "Microsoft Learn, IBM SkillsBuild, Cisco Networking Academy, "
        "Coursera (free audit), edX, freeCodeCamp, Kaggle Learn, and more.",
    )

    glass_card_open("🔍 Search & Filters")
    fc1, fc2 = st.columns([2, 1])
    with fc1:
        query = st.text_input("Search by course name or provider", placeholder="e.g. Python, IBM, UX")
    with fc2:
        domain = st.selectbox("Domain", ["All Domains", *DOMAINS])

    f1, f2, f3, f4 = st.columns(4)
    with f1:
        platform = st.selectbox("Platform", ["All Platforms", *PLATFORMS])
    with f2:
        difficulty = st.selectbox("Difficulty", ["All Levels", *DIFFICULTIES])
    with f3:
        duration = st.selectbox("Duration", DURATIONS)
    with f4:
        certificate_only = st.checkbox("Certificate only", value=False)
    glass_card_close()

    results = search_free_courses(
        domain=domain,
        query=query,
        platform=platform,
        difficulty=difficulty,
        duration=duration,
        certificate_only=certificate_only,
    )

    st.markdown(f"### Results ({len(results)})")
    if not results:
        empty_state("🔎", "No courses match those filters - try widening your search.")
        return

    cols = st.columns(2)
    for i, course in enumerate(results):
        with cols[i % 2]:
            _render_course_card(course)
