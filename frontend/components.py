"""
frontend/components.py
-------------------------
Reusable, presentation-only Streamlit UI components. Keeping these separate
from app.py keeps the main entrypoint thin and makes components testable /
reusable across pages.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

PRIORITY_CLASS = {"High": "pill-high", "Medium": "pill-medium", "Low": "pill-low"}


def hero(eyebrow: str, title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="hero">
            <span class="hero-eyebrow">{eyebrow}</span>
            <h1>{title}</h1>
            <p class="muted" style="max-width:640px;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, col=None) -> None:
    target = col if col is not None else st
    target.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-value">{value}</div>
            <div class="metric-label">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def glass_card_open(title: str = "") -> None:
    heading = f"<h3 style='margin-top:0'>{title}</h3>" if title else ""
    st.markdown(f"<div class='glass-card'>{heading}", unsafe_allow_html=True)


def glass_card_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def progress_bar(percent: int, label: str = "") -> None:
    percent = max(0, min(100, percent))
    label_html = f"<div class='muted' style='font-size:0.8rem;margin-bottom:4px;'>{label}</div>" if label else ""
    st.markdown(
        f"""
        {label_html}
        <div class="progress-track">
            <div class="progress-fill" style="width:{percent}%;"></div>
        </div>
        <div class="mono muted" style="font-size:0.75rem;margin-top:3px;">{percent}% complete</div>
        """,
        unsafe_allow_html=True,
    )


def pill(text: str, variant: str = "") -> str:
    cls = f"pill {variant}".strip()
    return f"<span class='{cls}'>{text}</span>"


def pill_row(items: list[str], variant: str = "") -> None:
    st.markdown("".join(pill(i, variant) for i in items), unsafe_allow_html=True)


def milestone_node(milestone: dict[str, Any]) -> None:
    week = milestone.get("week", "?")
    title = milestone.get("title", "")
    skills = milestone.get("key_skills", [])
    courses = milestone.get("recommended_courses", [])
    project = milestone.get("mini_project", "")
    tasks = milestone.get("practice_tasks", [])

    with st.container():
        st.markdown(
            f"""
            <div class="pathway-node">
                <span class="week-chip">WEEK {week}</span>
                <h4 style="margin:0 0 6px 0;">{title}</h4>
            </div>
            """,
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            if skills:
                st.markdown("**🎯 Key Skills**")
                pill_row(skills)
            if project:
                st.markdown(f"**🛠️ Mini Project**  \n{project}")
        with c2:
            if courses:
                st.markdown("**📚 Recommended Courses**")
                for c in courses:
                    st.markdown(f"- {c}")
            if tasks:
                st.markdown("**✅ Practice Tasks**")
                for t in tasks:
                    st.markdown(f"- {t}")
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)


def skill_gap_row(gap: dict[str, Any]) -> None:
    priority = gap.get("priority", "Medium")
    cls = PRIORITY_CLASS.get(priority, "")
    c1, c2, c3, c4 = st.columns([3, 2, 2, 1.4])
    c1.markdown(f"**{gap.get('skill', '-')}**")
    c2.markdown(f"<span class='mono muted'>{gap.get('current_level', '-')}</span>", unsafe_allow_html=True)
    c3.markdown(f"<span class='mono muted'>&rarr; {gap.get('required_level', '-')}</span>", unsafe_allow_html=True)
    c4.markdown(pill(priority, cls), unsafe_allow_html=True)


def course_card(course: Any, col=None) -> None:
    """Render a single recommended-course card with a direct clickable link."""
    target = col if col is not None else st
    target.markdown(
        f"""
        <div class="glass-card" style="padding:1.1rem 1.2rem;">
            <div style="font-weight:700; font-size:0.98rem; margin-bottom:2px;">{course.name}</div>
            <div class="muted" style="font-size:0.82rem; margin-bottom:8px;">{course.provider}</div>
            {pill(course.duration)} {pill(course.difficulty)} {pill(course.pricing, 'pill-low' if 'Free' in course.pricing else 'pill-medium')}
            <div style="margin-top:10px;">
                <a href="{course.link}" target="_blank" rel="noopener noreferrer"
                   style="text-decoration:none; font-weight:600; font-size:0.85rem; color: var(--violet);">
                   🔗 View Official Course →
                </a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def cert_card(cert: Any, col=None) -> None:
    """Render a single recommended-certification card with a direct clickable link."""
    target = col if col is not None else st
    target.markdown(
        f"""
        <div class="glass-card" style="padding:1.1rem 1.2rem;">
            <div style="font-weight:700; font-size:0.98rem; margin-bottom:2px;">🏅 {cert.name}</div>
            <div class="muted" style="font-size:0.82rem; margin-bottom:8px;">{cert.provider}</div>
            {pill(cert.difficulty)} {pill(cert.exam_cost)}
            <div style="margin-top:10px;">
                <a href="{cert.link}" target="_blank" rel="noopener noreferrer"
                   style="text-decoration:none; font-weight:600; font-size:0.85rem; color: var(--violet);">
                   🔗 View Official Certification →
                </a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def empty_state(icon: str, message: str) -> None:
    st.markdown(
        f"""
        <div class="glass-card" style="text-align:center; padding:2.4rem;">
            <div style="font-size:2.2rem;">{icon}</div>
            <p class="muted" style="margin-top:0.6rem;">{message}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
