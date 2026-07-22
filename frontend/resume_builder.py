"""
frontend/resume_builder.py
-----------------------------
Renders the "Resume Builder" page: a full ATS resume intake form with
support for multiple projects / certificates / internships, saving to
the "Users Resume Details" Google Sheet, and generating a downloadable
ATS-friendly PDF/DOCX.
"""

from __future__ import annotations

import streamlit as st

from backend.resume_store import (
    ResumeProfile, ProjectEntry, CertificateEntry, InternshipEntry, save_resume,
)
from backend.resume_generator import build_resume_pdf, build_resume_docx
from backend.logger_setup import get_logger
from frontend.components import hero, glass_card_open, glass_card_close

logger = get_logger(__name__)

_DYNAMIC_KEYS = {
    "resume_projects": "project",
    "resume_certificates": "certificate",
    "resume_internships": "internship",
}


def _init_state() -> None:
    for key in _DYNAMIC_KEYS:
        st.session_state.setdefault(key, [{}])
    st.session_state.setdefault("resume_profile", None)


def _dynamic_section(title: str, state_key: str, fields: list[tuple[str, str]]) -> list[dict]:
    """Render an 'Add another' repeating group of text inputs; return collected values."""
    st.markdown(f"**{title}**")
    entries = st.session_state[state_key]
    collected = []
    for i, entry in enumerate(entries):
        with st.container(border=True):
            values = {}
            cols = st.columns(len(fields))
            for (field_key, label), col in zip(fields, cols):
                values[field_key] = col.text_input(
                    label, value=entry.get(field_key, ""),
                    key=f"{state_key}_{field_key}_{i}",
                )
            collected.append(values)
    if st.button(f"➕ Add another {_DYNAMIC_KEYS[state_key]}", key=f"add_{state_key}"):
        st.session_state[state_key].append({})
        st.rerun()
    st.session_state[state_key] = collected
    return collected


def render_resume_builder_page() -> None:
    _init_state()
    user = st.session_state.get("auth_user") or {}

    hero(
        "ATS Resume Builder", "📄 Resume Builder",
        "Build a clean, single-column, ATS-friendly resume - fill in your "
        "details below, save your progress, then generate a PDF or Word download.",
    )

    glass_card_open("👤 Personal Details")
    c1, c2 = st.columns(2)
    first_name = c1.text_input("First Name *", value=user.get("first_name", ""))
    last_name = c2.text_input("Last Name *", value=user.get("last_name", ""))
    c3, c4 = st.columns(2)
    email = c3.text_input("Email *", value=user.get("email", ""))
    phone = c4.text_input("Phone *")
    address = st.text_input("Address")
    c5, c6, c7 = st.columns(3)
    linkedin = c5.text_input("LinkedIn URL")
    github = c6.text_input("GitHub URL")
    portfolio = c7.text_input("Portfolio URL")
    glass_card_close()

    glass_card_open("🎯 Career Objective")
    career_objective = st.text_area(
        "Career Objective", height=90,
        placeholder="2-3 sentences summarizing your goals and value proposition.",
    )
    glass_card_close()

    glass_card_open("🎓 Education")
    education = st.text_area(
        "Education (one entry per line)", height=90,
        placeholder="B.Tech in Computer Science, XYZ University, 2024, GPA 8.5/10",
    )
    glass_card_close()

    glass_card_open("🧠 Skills")
    skills_raw = st.text_area("Skills (comma-separated)", height=70,
                               placeholder="Python, SQL, Data Analysis, Communication")
    glass_card_close()

    glass_card_open("💼 Internships")
    internship_entries = _dynamic_section(
        "Internship Entries", "resume_internships",
        [("role", "Role"), ("company", "Company"), ("duration", "Duration")],
    )
    internship_descriptions = []
    for i, entry in enumerate(internship_entries):
        desc = st.text_area(f"Description - Internship {i + 1}", key=f"internship_desc_{i}", height=60)
        internship_descriptions.append(desc)
    glass_card_close()

    glass_card_open("🛠️ Projects")
    project_entries = _dynamic_section(
        "Project Entries", "resume_projects",
        [("title", "Project Title"), ("tech_stack", "Tech Stack")],
    )
    project_descriptions = []
    for i, entry in enumerate(project_entries):
        desc = st.text_area(f"Description - Project {i + 1}", key=f"project_desc_{i}", height=60)
        project_descriptions.append(desc)
    glass_card_close()

    glass_card_open("🏅 Certificates")
    certificate_entries = _dynamic_section(
        "Certificate Entries", "resume_certificates",
        [("name", "Certificate Name"), ("issuer", "Issuer"), ("year", "Year")],
    )
    glass_card_close()

    glass_card_open("🏆 Achievements")
    achievements = st.text_area("Achievements (one per line)", height=80)
    glass_card_close()

    glass_card_open("🌐 Languages & Hobbies")
    c8, c9 = st.columns(2)
    languages_raw = c8.text_input("Languages (comma-separated)")
    hobbies_raw = c9.text_input("Hobbies (comma-separated)")
    glass_card_close()

    glass_card_open("📇 References (optional)")
    references = st.text_area("References", height=70,
                               placeholder="Available upon request, or list name/relation/contact.")
    glass_card_close()

    def _build_profile() -> ResumeProfile:
        return ResumeProfile(
            first_name=first_name.strip(), last_name=last_name.strip(),
            email=email.strip(), phone=phone.strip(), address=address.strip(),
            linkedin=linkedin.strip(), github=github.strip(), portfolio=portfolio.strip(),
            career_objective=career_objective.strip(), education=education.strip(),
            skills=[s.strip() for s in skills_raw.split(",") if s.strip()],
            achievements=achievements.strip(),
            languages=[s.strip() for s in languages_raw.split(",") if s.strip()],
            hobbies=[s.strip() for s in hobbies_raw.split(",") if s.strip()],
            references=references.strip(),
            projects=[
                ProjectEntry(title=e.get("title", ""), tech_stack=e.get("tech_stack", ""), description=d)
                for e, d in zip(project_entries, project_descriptions) if e.get("title")
            ],
            certificates=[
                CertificateEntry(name=e.get("name", ""), issuer=e.get("issuer", ""), year=e.get("year", ""))
                for e in certificate_entries if e.get("name")
            ],
            internships=[
                InternshipEntry(role=e.get("role", ""), company=e.get("company", ""),
                                 duration=e.get("duration", ""), description=d)
                for e, d in zip(internship_entries, internship_descriptions) if e.get("role")
            ],
        )

    b1, b2, b3, b4 = st.columns(4)

    if b1.button("💾 Save Resume", use_container_width=True):
        if not (first_name and last_name and email):
            st.error("First Name, Last Name, and Email are required to save.")
        else:
            try:
                save_resume(_build_profile())
                st.success("✅ Resume details saved.")
            except Exception:
                logger.exception("Failed to save resume details")
                st.error("Couldn't save your resume details right now. Please try again.")

    if b2.button("✨ Generate Resume", use_container_width=True):
        if not (first_name and last_name and email):
            st.error("First Name, Last Name, and Email are required to generate a resume.")
        else:
            st.session_state["resume_profile"] = _build_profile()
            st.success("✅ Resume generated below - use the download buttons to save it.")

    profile: ResumeProfile | None = st.session_state["resume_profile"]

    with b3:
        if profile is not None:
            try:
                pdf_bytes = build_resume_pdf(profile)
                st.download_button(
                    "⬇️ Download PDF", data=pdf_bytes,
                    file_name=f"{profile.full_name.replace(' ', '_') or 'resume'}.pdf",
                    mime="application/pdf", use_container_width=True,
                )
            except Exception:
                logger.exception("PDF resume generation failed")
                st.error("Couldn't generate the PDF right now.")
        else:
            st.button("⬇️ Download PDF", disabled=True, use_container_width=True)

    with b4:
        if profile is not None:
            try:
                docx_bytes = build_resume_docx(profile)
                st.download_button(
                    "⬇️ Download DOCX", data=docx_bytes,
                    file_name=f"{profile.full_name.replace(' ', '_') or 'resume'}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )
            except Exception:
                logger.exception("DOCX resume generation failed")
                st.error("Couldn't generate the Word document right now.")
        else:
            st.button("⬇️ Download DOCX", disabled=True, use_container_width=True)

    if profile is not None:
        st.markdown("### 👁️ Preview")
        glass_card_open(profile.full_name or "Your Name")
        st.caption(" | ".join(p for p in [profile.phone, profile.email, profile.address] if p))
        if profile.career_objective:
            st.markdown(f"**Career Objective**  \n{profile.career_objective}")
        if profile.skills:
            st.markdown(f"**Skills**  \n{', '.join(profile.skills)}")
        glass_card_close()
