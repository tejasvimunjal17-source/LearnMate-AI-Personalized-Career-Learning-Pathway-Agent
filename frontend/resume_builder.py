"""
frontend/resume_builder.py
-----------------------------
Renders the "Resume Builder" page.

Education, Projects, Certificates, and Internships are all dynamic
add/remove card sections. Backend is untouched: Projects/Certificates/
Internships already map 1:1 onto backend.resume_store's ProjectEntry/
CertificateEntry/InternshipEntry dataclasses. Education has no dedicated
dataclass in the backend (ResumeProfile.education is a single str field),
so the structured education cards captured here are formatted into a
single well-structured multi-line string before being assigned to
ResumeProfile.education.

Resume Settings + templates + AI toolkit
------------------------------------------
This adds, ABOVE Personal Details, a "Resume Settings" panel: a
template gallery (backend.resume_templates), target role / experience
level / accent color / one-page toggle / photo show-hide, and a Live
Preview toggle. None of the original fields, session_state keys, or
Save/Generate/Download buttons were renamed or removed - all of this
is additive, using new session_state keys prefixed the same way
(`resume_*`) as the existing ones.

The AI Toolkit expander (ATS score, keyword suggestions, cover letter,
LinkedIn About, portfolio blurb, HR email, interview questions, resume
import/auto-fill, duplicate-skill detection, completeness meter) calls
backend.resume_ai / backend.resume_ats, which themselves wrap the
existing backend.openrouter_client and backend.resume_review pipelines
- no new external services or credentials.
"""

from __future__ import annotations

import uuid

import streamlit as st

from backend.resume_store import (
    ResumeProfile, ProjectEntry, CertificateEntry, InternshipEntry, save_resume,
)
from backend.resume_generator import build_resume_pdf, build_resume_docx
from backend.resume_templates import list_templates, get_template, ACCENT_COLORS, DEFAULT_TEMPLATE_ID
from backend.resume_ats import check_ats_score, suggest_keywords, resume_completeness, find_duplicate_skills
from backend.resume_ai import (
    generate_professional_summary, improve_bullet_point, polish_grammar,
    generate_cover_letter, generate_linkedin_about, generate_portfolio_blurb,
    generate_hr_email, generate_interview_questions, parse_resume_text_to_fields,
)
from backend.resume_review import extract_text_from_pdf, extract_text_from_docx
from backend.logger_setup import get_logger
from frontend.components import hero, glass_card_open, glass_card_close

logger = get_logger(__name__)

COLLEGE_LEVEL = "College / University"
SCHOOL_LEVEL = "School (10th / 12th)"
SCHOOL_QUALIFICATIONS = ["Secondary Education", "Senior Secondary Education"]
EXPERIENCE_LEVELS = ["Fresher", "Student", "Experienced"]

_LIST_STATE_KEYS = ["resume_education", "resume_projects", "resume_certificates", "resume_internships"]


# ------------------------------------------------------------------
# Session state helpers
# ------------------------------------------------------------------
def _new_id() -> str:
    return uuid.uuid4().hex[:8]


def _empty_education() -> dict:
    return {
        "_id": _new_id(), "level": COLLEGE_LEVEL,
        "degree": "", "field_major": "", "institution": "", "university_board": "",
        "start_year": "", "end_year": "", "present": False,
        "qualification": SCHOOL_QUALIFICATIONS[1], "school_name": "", "board": "",
        "passing_year": "",
        "city": "", "state": "", "country": "", "grade": "",
    }


def _empty_project() -> dict:
    return {"_id": _new_id(), "title": "", "tech_stack": "", "description": ""}


def _empty_certificate() -> dict:
    return {"_id": _new_id(), "name": "", "issuer": "", "year": ""}


def _empty_internship() -> dict:
    return {"_id": _new_id(), "role": "", "company": "", "duration": "", "description": ""}


_EMPTY_FACTORIES = {
    "resume_education": _empty_education,
    "resume_projects": _empty_project,
    "resume_certificates": _empty_certificate,
    "resume_internships": _empty_internship,
}


def _init_state() -> None:
    for key in _LIST_STATE_KEYS:
        if key not in st.session_state or not st.session_state[key]:
            st.session_state[key] = [_EMPTY_FACTORIES[key]()]
    st.session_state.setdefault("resume_profile", None)
    # Resume Settings (additive, new keys only)
    st.session_state.setdefault("resume_template_id", DEFAULT_TEMPLATE_ID)
    st.session_state.setdefault("resume_target_role", "")
    st.session_state.setdefault("resume_experience_level", "Fresher")
    st.session_state.setdefault("resume_accent_color_name", "Blue")
    st.session_state.setdefault("resume_one_page", True)
    st.session_state.setdefault("resume_show_photo", False)
    st.session_state.setdefault("resume_photo_bytes", None)
    st.session_state.setdefault("resume_summary", "")
    st.session_state.setdefault("resume_live_preview", True)
    # Personal details (now keyed so AI import can populate them)
    st.session_state.setdefault("resume_first_name", None)
    st.session_state.setdefault("resume_last_name", None)
    st.session_state.setdefault("resume_email", None)
    st.session_state.setdefault("resume_achievements", "")
    st.session_state.setdefault("resume_hobbies_raw", "")
    st.session_state.setdefault("resume_skills_raw", "")
    # AI toolkit result caches
    for k in ("ats_result", "keyword_suggestions", "cover_letter", "linkedin_about",
              "portfolio_blurb", "hr_email", "interview_questions", "import_message"):
        st.session_state.setdefault(f"resume_ai_{k}", None)
    # Holds a parsed "Import Resume" dict between reruns. NOT a widget key
    # itself - see _apply_pending_import()/_render_import_section() for why
    # this indirection exists (it's what fixes the resume_target_role crash).
    st.session_state.setdefault("_resume_import_pending", None)


def _remove_entry(state_key: str, entry_id: str) -> None:
    entries = st.session_state[state_key]
    if len(entries) <= 1:
        return
    st.session_state[state_key] = [e for e in entries if e["_id"] != entry_id]
    st.rerun()


def _add_entry(state_key: str) -> None:
    st.session_state[state_key].append(_EMPTY_FACTORIES[state_key]())
    st.rerun()


def _card_header(label: str, state_key: str, entry_id: str, can_remove: bool) -> None:
    head_col, remove_col = st.columns([6, 1])
    head_col.markdown(f"**{label}**")
    with remove_col:
        if st.button("❌", key=f"remove_{state_key}_{entry_id}",
                      disabled=not can_remove, help="Remove this entry"):
            _remove_entry(state_key, entry_id)


# ------------------------------------------------------------------
# Resume Settings: template gallery
# ------------------------------------------------------------------
def _render_template_gallery() -> None:
    templates = list_templates()
    selected = st.session_state["resume_template_id"]
    cols = st.columns(len(templates))

    for col, tpl in zip(cols, templates):
        is_selected = tpl.id == selected
        border_color = "#2563EB" if is_selected else "rgba(255,255,255,0.12)"
        with col:
            st.markdown(
                f"""
                <div style="border:2px solid {border_color}; border-radius:12px; padding:12px;
                            min-height:150px; background:rgba(255,255,255,0.03);">
                    <div style="font-weight:700; font-size:0.98rem;">
                        {'⭐ ' if is_selected else ''}{tpl.name}
                    </div>
                    <div style="font-size:0.8rem; opacity:0.75; margin:2px 0 6px;">{tpl.tagline}</div>
                    <div style="font-size:0.75rem; opacity:0.65; line-height:1.3;">{tpl.description}</div>
                    <div style="margin-top:8px; display:inline-block; font-size:0.72rem;
                                background:rgba(34,211,176,0.12); color:#22D3B0; border:1px solid rgba(34,211,176,0.4);
                                border-radius:999px; padding:2px 8px;">
                        ATS Score {tpl.ats_score}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            btn_label = "✅ Selected" if is_selected else "Select"
            if st.button(btn_label, key=f"select_tpl_{tpl.id}", use_container_width=True,
                         disabled=is_selected):
                st.session_state["resume_template_id"] = tpl.id
                st.rerun()


def _render_resume_settings() -> None:
    glass_card_open("⚙️ Resume Settings")
    st.caption("Pick a template and a few preferences - everything below still maps onto "
               "the same form fields further down. No new data required to generate a resume.")

    st.markdown("**Resume Template**")
    _render_template_gallery()

    st.markdown("&nbsp;", unsafe_allow_html=True)
    # Note: these widgets bind directly to session_state via `key=` (no
    # `value=` passed alongside it) so that programmatic updates - e.g.
    # from the "Import Resume" auto-fill feature - can update them by
    # writing to st.session_state before the next rerun.
    c1, c2, c3 = st.columns(3)
    c1.text_input("Target Job Role", key="resume_target_role", placeholder="e.g. Software Engineer")
    c2.selectbox("Experience Level", EXPERIENCE_LEVELS, key="resume_experience_level")
    c3.selectbox("Resume Language", ["English"], index=0, disabled=True,
                 help="More languages coming soon.")

    c4, c5, c6 = st.columns(3)
    c4.selectbox("Accent Color", list(ACCENT_COLORS.keys()), key="resume_accent_color_name")
    c5.toggle("One Page", key="resume_one_page",
              help="Off = a slightly more relaxed, two-page-friendly layout.")
    c6.toggle("Show Photo", key="resume_show_photo")

    if st.session_state["resume_show_photo"]:
        photo_file = st.file_uploader(
            "Upload a headshot (used for this download only, not saved to your account)",
            type=["png", "jpg", "jpeg"], key="resume_photo_uploader",
        )
        if photo_file is not None:
            st.session_state["resume_photo_bytes"] = photo_file.read()

    st.toggle("Live Resume Preview", key="resume_live_preview")
    glass_card_close()


# ------------------------------------------------------------------
# Education cards (unchanged from the original builder)
# ------------------------------------------------------------------
def _render_education_entries() -> list[dict]:
    entries = st.session_state["resume_education"]
    can_remove = len(entries) > 1

    for idx, entry in enumerate(entries):
        eid = entry["_id"]
        with st.container(border=True):
            _card_header(f"Education Entry {idx + 1}", "resume_education", eid, can_remove)

            entry["level"] = st.selectbox(
                "Education Level", [COLLEGE_LEVEL, SCHOOL_LEVEL],
                index=[COLLEGE_LEVEL, SCHOOL_LEVEL].index(entry["level"]),
                key=f"edu_level_{eid}",
            )

            if entry["level"] == COLLEGE_LEVEL:
                c1, c2 = st.columns(2)
                entry["degree"] = c1.text_input(
                    "Degree (e.g. Bachelor of Commerce (Hons))",
                    value=entry["degree"], key=f"edu_degree_{eid}",
                )
                entry["field_major"] = c2.text_input(
                    "Field / Major", value=entry["field_major"], key=f"edu_field_{eid}",
                )
                c3, c4 = st.columns(2)
                entry["institution"] = c3.text_input(
                    "College / University Name", value=entry["institution"], key=f"edu_inst_{eid}",
                )
                entry["university_board"] = c4.text_input(
                    "University / Board", value=entry["university_board"], key=f"edu_univ_{eid}",
                )
                c5, c6, c7 = st.columns([1, 1, 1])
                entry["start_year"] = c5.text_input(
                    "Start Year", value=entry["start_year"], key=f"edu_start_{eid}",
                )
                entry["present"] = c6.checkbox(
                    "Present", value=entry["present"], key=f"edu_present_{eid}",
                )
                entry["end_year"] = c7.text_input(
                    "End Year", value=entry["end_year"], key=f"edu_end_{eid}",
                    disabled=entry["present"],
                )
                c8, c9, c10 = st.columns(3)
                entry["city"] = c8.text_input("City", value=entry["city"], key=f"edu_city_{eid}")
                entry["state"] = c9.text_input("State", value=entry["state"], key=f"edu_state_{eid}")
                entry["country"] = c10.text_input("Country", value=entry["country"], key=f"edu_country_{eid}")
                entry["grade"] = st.text_input(
                    "CGPA / Percentage (optional)", value=entry["grade"], key=f"edu_grade_{eid}",
                )
            else:
                entry["qualification"] = st.selectbox(
                    "Qualification", SCHOOL_QUALIFICATIONS,
                    index=SCHOOL_QUALIFICATIONS.index(entry["qualification"])
                    if entry["qualification"] in SCHOOL_QUALIFICATIONS else 1,
                    key=f"edu_qual_{eid}",
                )
                c1, c2 = st.columns(2)
                entry["school_name"] = c1.text_input(
                    "School Name", value=entry["school_name"], key=f"edu_school_{eid}",
                )
                entry["board"] = c2.text_input(
                    "Education Board (CBSE / ICSE / State Board / IB / etc.)",
                    value=entry["board"], key=f"edu_board_{eid}",
                )
                entry["passing_year"] = st.text_input(
                    "Passing Year", value=entry["passing_year"], key=f"edu_passing_{eid}",
                )
                c3, c4, c5 = st.columns(3)
                entry["city"] = c3.text_input("City", value=entry["city"], key=f"edu_scity_{eid}")
                entry["state"] = c4.text_input("State", value=entry["state"], key=f"edu_sstate_{eid}")
                entry["country"] = c5.text_input("Country", value=entry["country"], key=f"edu_scountry_{eid}")
                entry["grade"] = st.text_input(
                    "Percentage / CGPA (optional)", value=entry["grade"], key=f"edu_sgrade_{eid}",
                )

    if st.button("➕ Add Education", key="add_resume_education"):
        _add_entry("resume_education")

    return entries


def _format_education_entry(e: dict) -> str:
    location = ", ".join(p for p in [e.get("city", ""), e.get("state", ""), e.get("country", "")] if p)

    if e["level"] == COLLEGE_LEVEL:
        title_line = e["degree"] or e["field_major"]
        status = "Pursuing" if e["present"] else (e["end_year"] or "")
        if title_line and status:
            title_line = f"{title_line} | {status}"
        years = f"{e['start_year']} – {'Present' if e['present'] else e['end_year']}".strip(" –")
        last_line = f"{years}          {location}".strip() if (years or location) else ""
        lines = [title_line, e["institution"], e["university_board"], last_line]
    else:
        years = e["passing_year"]
        last_line = f"{years}          {location}".strip() if (years or location) else ""
        lines = [e["qualification"], e["school_name"], e["board"], last_line]

    lines = [l for l in lines if l and l.strip()]
    if e.get("grade"):
        lines.append(f"Grade: {e['grade']}")
    return "\n".join(lines)


def _education_entries_to_text(entries: list[dict]) -> str:
    blocks = [_format_education_entry(e) for e in entries]
    blocks = [b for b in blocks if b.strip()]
    return "\n".join(blocks)


# ------------------------------------------------------------------
# Projects / Certificates / Internships cards
# ------------------------------------------------------------------
def _render_project_entries() -> list[dict]:
    entries = st.session_state["resume_projects"]
    can_remove = len(entries) > 1
    for idx, entry in enumerate(entries):
        eid = entry["_id"]
        with st.container(border=True):
            _card_header(f"Project {idx + 1}", "resume_projects", eid, can_remove)
            c1, c2 = st.columns(2)
            entry["title"] = c1.text_input("Project Title", value=entry["title"], key=f"proj_title_{eid}")
            entry["tech_stack"] = c2.text_input("Tech Stack", value=entry["tech_stack"], key=f"proj_tech_{eid}")
            entry["description"] = st.text_area(
                "Description", value=entry["description"], key=f"proj_desc_{eid}", height=70,
            )
            if st.button("✨ Improve wording", key=f"proj_improve_{eid}"):
                with st.spinner("Rewriting..."):
                    entry["description"] = improve_bullet_point(
                        entry["description"], st.session_state["resume_target_role"]
                    )
                st.rerun()
    if st.button("➕ Add Another Project", key="add_resume_projects"):
        _add_entry("resume_projects")
    return entries


def _render_certificate_entries() -> list[dict]:
    entries = st.session_state["resume_certificates"]
    can_remove = len(entries) > 1
    for idx, entry in enumerate(entries):
        eid = entry["_id"]
        with st.container(border=True):
            _card_header(f"Certificate {idx + 1}", "resume_certificates", eid, can_remove)
            c1, c2, c3 = st.columns(3)
            entry["name"] = c1.text_input("Certificate Name", value=entry["name"], key=f"cert_name_{eid}")
            entry["issuer"] = c2.text_input("Issuer", value=entry["issuer"], key=f"cert_issuer_{eid}")
            entry["year"] = c3.text_input("Year", value=entry["year"], key=f"cert_year_{eid}")
    if st.button("➕ Add Another Certificate", key="add_resume_certificates"):
        _add_entry("resume_certificates")
    return entries


def _render_internship_entries() -> list[dict]:
    entries = st.session_state["resume_internships"]
    can_remove = len(entries) > 1
    for idx, entry in enumerate(entries):
        eid = entry["_id"]
        with st.container(border=True):
            _card_header(f"Internship {idx + 1}", "resume_internships", eid, can_remove)
            c1, c2, c3 = st.columns(3)
            entry["role"] = c1.text_input("Role", value=entry["role"], key=f"intern_role_{eid}")
            entry["company"] = c2.text_input("Company", value=entry["company"], key=f"intern_company_{eid}")
            entry["duration"] = c3.text_input("Duration", value=entry["duration"], key=f"intern_duration_{eid}")
            entry["description"] = st.text_area(
                "Description", value=entry["description"], key=f"intern_desc_{eid}", height=70,
            )
            if st.button("✨ Improve wording", key=f"intern_improve_{eid}"):
                with st.spinner("Rewriting..."):
                    entry["description"] = improve_bullet_point(
                        entry["description"], st.session_state["resume_target_role"]
                    )
                st.rerun()
    if st.button("➕ Add Another Internship", key="add_resume_internships"):
        _add_entry("resume_internships")
    return entries


# ------------------------------------------------------------------
# Resume import / auto-fill
# ------------------------------------------------------------------
def _apply_imported_fields(data: dict) -> None:
    """Map an AI-parsed import dict onto the existing form's session_state."""
    if data.get("first_name"):
        st.session_state["resume_first_name"] = data["first_name"]
    if data.get("last_name"):
        st.session_state["resume_last_name"] = data["last_name"]
    if data.get("email"):
        st.session_state["resume_email"] = data["email"]
    if data.get("target_role"):
        st.session_state["resume_target_role"] = data["target_role"]
    if data.get("summary"):
        st.session_state["resume_summary"] = data["summary"]
    if data.get("skills"):
        st.session_state["resume_skills_raw"] = ", ".join(str(s) for s in data["skills"])
    if data.get("hobbies"):
        st.session_state["resume_hobbies_raw"] = ", ".join(str(h) for h in data["hobbies"])
    if data.get("achievements"):
        st.session_state["resume_achievements"] = str(data["achievements"])

    if data.get("education"):
        edu_lines = [l.strip() for l in str(data["education"]).splitlines() if l.strip()]
        entry = _empty_education()
        if edu_lines:
            entry["degree"] = edu_lines[0]
        if len(edu_lines) > 1:
            entry["institution"] = edu_lines[1]
        if len(edu_lines) > 2:
            entry["university_board"] = edu_lines[2]
        st.session_state["resume_education"] = [entry]

    if data.get("projects"):
        st.session_state["resume_projects"] = [
            {**_empty_project(), "title": p.get("title", ""), "tech_stack": p.get("tech_stack", ""),
             "description": p.get("description", "")}
            for p in data["projects"] if isinstance(p, dict) and (p.get("title") or p.get("description"))
        ] or st.session_state["resume_projects"]

    if data.get("internships"):
        st.session_state["resume_internships"] = [
            {**_empty_internship(), "role": i.get("role", ""), "company": i.get("company", ""),
             "duration": i.get("duration", ""), "description": i.get("description", "")}
            for i in data["internships"] if isinstance(i, dict) and (i.get("role") or i.get("description"))
        ] or st.session_state["resume_internships"]

    if data.get("certificates"):
        st.session_state["resume_certificates"] = [
            {**_empty_certificate(), "name": c.get("name", ""), "issuer": c.get("issuer", ""),
             "year": c.get("year", "")}
            for c in data["certificates"] if isinstance(c, dict) and c.get("name")
        ] or st.session_state["resume_certificates"]


def _apply_pending_import() -> None:
    """Apply a previously-parsed "Import Resume" dict to session_state.

    MUST be called before any widget bound to one of these keys (e.g. the
    `resume_target_role` text_input in _render_resume_settings) is
    instantiated in this run - Streamlit forbids writing to
    st.session_state[key] once a widget with that key has already been
    created during the same script run.

    The import button below never applies data directly for that exact
    reason: it only stashes the parsed dict under the internal
    "_resume_import_pending" key (which no widget uses) and reruns. On
    the *next* run, this function runs first - before _render_resume_settings()
    or any form field - so every st.session_state[...] write here is safe.
    """
    pending = st.session_state.get("_resume_import_pending")
    if pending is not None:
        _apply_imported_fields(pending)
        st.session_state["_resume_import_pending"] = None
        st.session_state["resume_ai_import_message"] = "✅ Form auto-filled - review and edit below."


def _render_import_section() -> None:
    with st.expander("📥 Import an existing resume (PDF/DOCX) to auto-fill this form"):
        uploaded = st.file_uploader("Upload resume", type=["pdf", "docx"], key="resume_import_uploader")
        if st.button("Import & Auto-fill", key="resume_import_btn", disabled=uploaded is None):
            st.session_state["resume_ai_import_message"] = None
            try:
                with st.status("Importing resume...", expanded=True) as status:
                    status.write("📤 Uploading resume...")
                    raw_bytes = uploaded.read()
                    name = (uploaded.name or "").lower()
                    is_pdf = uploaded.type == "application/pdf" or name.endswith(".pdf")

                    status.write("🔎 Extracting text...")
                    text = extract_text_from_pdf(raw_bytes) if is_pdf else extract_text_from_docx(raw_bytes)

                    if not text:
                        status.update(label="Couldn't read that file", state="error")
                        st.session_state["resume_ai_import_message"] = (
                            "Couldn't extract any text from that file - it may be a scanned "
                            "image with no selectable text. Please fill the fields manually, "
                            "or try uploading a text-based (not scanned) PDF/DOCX."
                        )
                    else:
                        status.write("🤖 Analyzing with AI...")
                        data = parse_resume_text_to_fields(text)

                        if not data:
                            status.update(label="Couldn't parse that resume", state="error")
                            st.session_state["resume_ai_import_message"] = (
                                "Could not extract resume. Please fill the fields manually."
                            )
                        else:
                            status.write("✍️ Populating resume...")
                            # Don't touch resume_* widget keys here - stash the
                            # data and rerun; _apply_pending_import() (called
                            # at the very top of the page, before any widget
                            # exists) does the actual session_state writes.
                            st.session_state["_resume_import_pending"] = data
                            status.update(label="Done", state="complete")
            except Exception as exc:  # noqa: BLE001 - importing must never crash the app
                logger.error("Resume import failed unexpectedly: %s", exc)
                st.session_state["resume_ai_import_message"] = (
                    "Could not extract resume. Please fill the fields manually."
                )
            st.rerun()
        if st.session_state["resume_ai_import_message"]:
            st.info(st.session_state["resume_ai_import_message"])


# ------------------------------------------------------------------
# AI Toolkit
# ------------------------------------------------------------------
def _render_ai_toolkit(preview_profile: ResumeProfile) -> None:
    with st.expander("🤖 AI Resume Toolkit", expanded=False):
        completeness = resume_completeness(preview_profile)
        st.progress(completeness.percent / 100, text=f"Resume Completeness: {completeness.percent}%")
        if completeness.missing:
            st.caption("Still missing: " + ", ".join(completeness.missing))

        dupes = find_duplicate_skills(preview_profile.skills)
        if dupes:
            st.warning(f"Duplicate skills detected: {', '.join(dupes)}")

        t1, t2, t3, t4 = st.tabs(["ATS Score", "Cover Letter / LinkedIn", "Portfolio / HR Email", "Interview Prep"])

        with t1:
            if st.button("🎯 Check ATS Score", key="ai_ats_btn"):
                with st.spinner("Scoring..."):
                    st.session_state["resume_ai_ats_result"] = check_ats_score(preview_profile)
            if st.button("🔑 Suggest Keywords", key="ai_kw_btn"):
                with st.spinner("Finding relevant keywords..."):
                    st.session_state["resume_ai_keyword_suggestions"] = suggest_keywords(preview_profile)

            result = st.session_state["resume_ai_ats_result"]
            if result is not None:
                st.metric("ATS Score", f"{result.ats_score}/100")
                if result.missing_sections:
                    st.caption("Missing sections: " + ", ".join(result.missing_sections))
                for tip in result.suggestions[:6]:
                    st.markdown(f"- {tip}")

            kws = st.session_state["resume_ai_keyword_suggestions"]
            if kws:
                st.caption("Consider adding (if relevant): " + ", ".join(kws))
                if st.button("➕ Add these to my Skills", key="ai_add_kw_btn"):
                    current = [s.strip() for s in st.session_state["resume_skills_raw"].split(",") if s.strip()]
                    st.session_state["resume_skills_raw"] = ", ".join(dict.fromkeys(current + kws))
                    st.rerun()

        with t2:
            # These four use st.code() rather than st.text_area() for the
            # generated output. A text_area with its own separate key
            # would "freeze" after the first generation: clicking
            # Generate/Regenerate a second time updates
            # resume_ai_cover_letter etc., but Streamlit hands display
            # authority for a *keyed* widget to whatever's already stored
            # under THAT widget's own key - not to a fresh `value=` - so a
            # second click would silently keep showing the first result.
            # st.code() has no independent widget state, so it always
            # reflects the current session_state value, and gets a
            # copy-to-clipboard button as a bonus.
            cc1, cc2 = st.columns(2)
            company = cc1.text_input("Company (optional)", key="ai_cover_company")
            if cc2.button("✉️ Generate Cover Letter", key="ai_cover_btn"):
                with st.spinner("Drafting..."):
                    st.session_state["resume_ai_cover_letter"] = generate_cover_letter(preview_profile, company)
            if st.session_state["resume_ai_cover_letter"]:
                st.caption("Cover Letter")
                st.code(st.session_state["resume_ai_cover_letter"], language=None, wrap_lines=True)

            if st.button("💼 Generate LinkedIn About", key="ai_linkedin_btn"):
                with st.spinner("Drafting..."):
                    st.session_state["resume_ai_linkedin_about"] = generate_linkedin_about(preview_profile)
            if st.session_state["resume_ai_linkedin_about"]:
                st.caption("LinkedIn About")
                st.code(st.session_state["resume_ai_linkedin_about"], language=None, wrap_lines=True)

        with t3:
            if st.button("🌐 Generate Portfolio Intro", key="ai_portfolio_btn"):
                with st.spinner("Drafting..."):
                    st.session_state["resume_ai_portfolio_blurb"] = generate_portfolio_blurb(preview_profile)
            if st.session_state["resume_ai_portfolio_blurb"]:
                st.caption("Portfolio Homepage Intro")
                st.code(st.session_state["resume_ai_portfolio_blurb"], language=None, wrap_lines=True)

            purpose = st.text_input("Email purpose", value="job application follow-up", key="ai_hr_purpose")
            if st.button("📧 Generate HR Email", key="ai_hr_btn"):
                with st.spinner("Drafting..."):
                    st.session_state["resume_ai_hr_email"] = generate_hr_email(preview_profile, purpose)
            if st.session_state["resume_ai_hr_email"]:
                st.caption("HR Email")
                st.code(st.session_state["resume_ai_hr_email"], language=None, wrap_lines=True)

        with t4:
            if st.button("🧠 Generate Interview Questions", key="ai_interview_btn"):
                with st.spinner("Thinking..."):
                    st.session_state["resume_ai_interview_questions"] = generate_interview_questions(preview_profile)
            if st.session_state["resume_ai_interview_questions"]:
                st.markdown(st.session_state["resume_ai_interview_questions"])


# ------------------------------------------------------------------
# Live preview (template-aware HTML card)
# ------------------------------------------------------------------
def _render_live_preview(profile: ResumeProfile) -> None:
    template = get_template(profile.template_id)
    accent = profile.accent_color or "#2563EB"
    style = template.style
    is_banner = style.header_style == "banner"
    is_center = style.name_align == "center"

    header_bg = f"background:{accent}; color:white; border-radius:8px 8px 0 0;" if is_banner else ""
    align = "text-align:center;" if is_center else ""
    name_color = "white" if is_banner else ("#111827" if style.header_style != "sidebar-bar" else accent)

    def esc(s: str) -> str:
        return (s or "").replace("<", "&lt;").replace(">", "&gt;")

    sections_html = ""
    if profile.summary:
        sections_html += f"<h4 style='color:{accent}; margin-bottom:2px;'>Professional Summary</h4><p>{esc(profile.summary)}</p>"
    if profile.education:
        edu_html = esc(profile.education).replace("\n", "<br>")
        sections_html += f"<h4 style='color:{accent}; margin-bottom:2px;'>Education</h4><p>{edu_html}</p>"
    if profile.skills:
        sections_html += f"<h4 style='color:{accent}; margin-bottom:2px;'>Skills</h4><p>{esc(', '.join(profile.skills))}</p>"
    if profile.internships:
        rows = "".join(
            f"<p><b>{esc(i.role)}</b> - {esc(i.company)} ({esc(i.duration)})<br>{esc(i.description)}</p>"
            for i in profile.internships
        )
        sections_html += f"<h4 style='color:{accent}; margin-bottom:2px;'>Experience</h4>{rows}"
    if profile.projects:
        rows = "".join(
            f"<p><b>{esc(p.title)}</b> ({esc(p.tech_stack)})<br>{esc(p.description)}</p>"
            for p in profile.projects
        )
        sections_html += f"<h4 style='color:{accent}; margin-bottom:2px;'>Projects</h4>{rows}"

    st.markdown(
        f"""
        <div style="background:white; color:#1f2937; border-radius:8px; overflow:hidden;
                    box-shadow:0 4px 20px rgba(0,0,0,0.25); max-width:680px;">
            <div style="padding:18px 22px; {header_bg} {align}">
                <div style="font-size:1.4rem; font-weight:700; color:{name_color};">{esc(profile.full_name) or 'Your Name'}</div>
                <div style="font-size:0.85rem; opacity:0.85; color:{'white' if is_banner else accent};">{esc(profile.target_role)}</div>
                <div style="font-size:0.78rem; opacity:0.75; color:{'white' if is_banner else '#4b5563'};">{esc(profile.email)}</div>
            </div>
            <div style="padding:16px 22px; font-size:0.85rem; line-height:1.4;">
                {sections_html or "<p style='opacity:0.6;'>Fill in the form to see your resume take shape here.</p>"}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------------
# Page
# ------------------------------------------------------------------
def render_resume_builder_page():
    _init_state()
    # Must run before ANY resume_* widget below (Resume Settings, Personal
    # Details, etc.) is instantiated - see _apply_pending_import()'s
    # docstring for why.
    _apply_pending_import()
    user = st.session_state.get("auth_user") or {}
    if st.session_state["resume_first_name"] is None:
        st.session_state["resume_first_name"] = user.get("first_name", "")
    if st.session_state["resume_last_name"] is None:
        st.session_state["resume_last_name"] = user.get("last_name", "")
    if st.session_state["resume_email"] is None:
        st.session_state["resume_email"] = user.get("email", "")

    hero(
        "ATS Resume Builder", "📄 Resume Builder",
        "Build a clean, ATS-friendly resume - pick a template, fill in your "
        "details below, save your progress, then generate a PDF or Word download.",
    )

    _render_resume_settings()
    _render_import_section()

    glass_card_open("👤 Personal Details")
    c1, c2 = st.columns(2)
    first_name = c1.text_input("First Name *", key="resume_first_name")
    last_name = c2.text_input("Last Name *", key="resume_last_name")
    email = st.text_input("Email *", key="resume_email")
    glass_card_close()

    glass_card_open("📝 Professional Summary")
    sc1, sc2 = st.columns([4, 1])
    with sc2:
        if st.button("✨ Generate from data", key="ai_summary_btn", use_container_width=True):
            with st.spinner("Writing..."):
                draft_profile = ResumeProfile(
                    first_name=first_name, last_name=last_name, email=email,
                    education=_education_entries_to_text(st.session_state["resume_education"]),
                    skills=[s.strip() for s in st.session_state["resume_skills_raw"].split(",") if s.strip()],
                    target_role=st.session_state["resume_target_role"],
                    experience_level=st.session_state["resume_experience_level"],
                    internships=[InternshipEntry(role=e["role"], company=e["company"],
                                                  duration=e["duration"], description=e["description"])
                                 for e in st.session_state["resume_internships"] if e["role"].strip()],
                    projects=[ProjectEntry(title=e["title"], tech_stack=e["tech_stack"],
                                            description=e["description"])
                              for e in st.session_state["resume_projects"] if e["title"].strip()],
                )
                st.session_state["resume_summary"] = generate_professional_summary(draft_profile)
            st.rerun()
        if st.button("✅ Grammar Check", key="ai_grammar_btn", use_container_width=True):
            with st.spinner("Polishing..."):
                st.session_state["resume_summary"] = polish_grammar(st.session_state["resume_summary"])
            st.rerun()
    with sc1:
        # key="resume_summary" directly - NOT a separate "_input" key - so
        # that setting st.session_state["resume_summary"] from the AI
        # Generate/Grammar Check buttons above (or from Import Resume)
        # actually changes what's displayed here. A mismatched key would
        # make Streamlit ignore the `value=` after the first render.
        st.text_area("2-3 sentence summary (optional)", height=90, key="resume_summary")
    glass_card_close()

    glass_card_open("🎓 Education")
    education_entries = _render_education_entries()
    glass_card_close()

    glass_card_open("🧠 Skills")
    # key="resume_skills_raw" (not just value=) so the AI Toolkit's
    # "Add these to my Skills" button and Import Resume auto-fill can
    # actually change what's shown here.
    st.text_area(
        "Skills (comma-separated)", height=70, key="resume_skills_raw",
        placeholder="Python, SQL, Data Analysis, Communication",
    )
    glass_card_close()

    glass_card_open("💼 Internships")
    internship_entries = _render_internship_entries()
    glass_card_close()

    glass_card_open("🛠️ Projects")
    project_entries = _render_project_entries()
    glass_card_close()

    glass_card_open("🏅 Certificates")
    certificate_entries = _render_certificate_entries()
    glass_card_close()

    glass_card_open("🏆 Achievements")
    # key="resume_achievements" so Import Resume auto-fill can update it.
    st.text_area("Achievements (one per line)", height=80, key="resume_achievements")
    glass_card_close()

    glass_card_open("🌐 Hobbies")
    # key="resume_hobbies_raw" so Import Resume auto-fill can update it.
    st.text_input("Hobbies (comma-separated)", key="resume_hobbies_raw")
    glass_card_close()

    def _build_profile() -> ResumeProfile:
        return ResumeProfile(
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            email=email.strip(),
            education=_education_entries_to_text(education_entries),
            skills=[s.strip() for s in st.session_state["resume_skills_raw"].split(",") if s.strip()],
            achievements=st.session_state["resume_achievements"].strip(),
            hobbies=[s.strip() for s in st.session_state["resume_hobbies_raw"].split(",") if s.strip()],
            projects=[
                ProjectEntry(title=e["title"], tech_stack=e["tech_stack"], description=e["description"])
                for e in project_entries if e["title"].strip()
            ],
            certificates=[
                CertificateEntry(name=e["name"], issuer=e["issuer"], year=e["year"])
                for e in certificate_entries if e["name"].strip()
            ],
            internships=[
                InternshipEntry(role=e["role"], company=e["company"],
                                 duration=e["duration"], description=e["description"])
                for e in internship_entries if e["role"].strip()
            ],
            template_id=st.session_state["resume_template_id"],
            target_role=st.session_state["resume_target_role"].strip(),
            experience_level=st.session_state["resume_experience_level"],
            summary=st.session_state["resume_summary"].strip(),
            accent_color=ACCENT_COLORS.get(st.session_state["resume_accent_color_name"], "#2563EB"),
            one_page=st.session_state["resume_one_page"],
            show_photo=st.session_state["resume_show_photo"],
        )

    _render_ai_toolkit(_build_profile())

    b1, b2, b3, b4 = st.columns(4)

    if b1.button("💾 Save Resume", use_container_width=True):
        if not (first_name and last_name and email):
            st.error("First Name, Last Name, and Email are required to save.")
        else:
            try:
                save_resume(_build_profile())
                st.success("✅ Resume details saved.")
            except Exception as exc:
                st.error(f"Couldn't save your resume details right now: {exc}")

    if b2.button("✨ Generate Resume", use_container_width=True):
        if not (first_name and last_name and email):
            st.error("First Name, Last Name, and Email are required to generate a resume.")
        else:
            st.session_state["resume_profile"] = _build_profile()
            st.success("✅ Resume generated below - use the download buttons to save it.")

    profile: ResumeProfile | None = st.session_state["resume_profile"]
    photo_bytes = st.session_state["resume_photo_bytes"] if st.session_state["resume_show_photo"] else None

    with b3:
        if profile is not None:
            try:
                pdf_bytes = build_resume_pdf(profile, photo_bytes=photo_bytes)
                st.download_button(
                    "⬇️ Download PDF", data=pdf_bytes,
                    file_name=f"{profile.full_name.replace(' ', '_') or 'resume'}.pdf",
                    mime="application/pdf", use_container_width=True,
                )
            except Exception as exc:
                st.error(f"Couldn't generate the PDF right now: {exc}")
        else:
            st.button("⬇️ Download PDF", disabled=True, use_container_width=True)

    with b4:
        if profile is not None:
            try:
                docx_bytes = build_resume_docx(profile, photo_bytes=photo_bytes)
                st.download_button(
                    "⬇️ Download DOCX", data=docx_bytes,
                    file_name=f"{profile.full_name.replace(' ', '_') or 'resume'}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )
            except Exception as exc:
                st.error(f"Couldn't generate the Word document right now: {exc}")
        else:
            st.button("⬇️ Download DOCX", disabled=True, use_container_width=True)

    if st.session_state["resume_live_preview"]:
        st.markdown("### 👁️ Live Preview")
        _render_live_preview(_build_profile())

    if not email:
        st.caption("Add your email above so your resume can be saved and retrieved later.")


# End of frontend/resume_builder.py