"""
backend/resume_ats.py
------------------------
ATS Score Checker, Keyword Suggestions, Resume Completeness Meter, and
Duplicate Skill Detection for the Resume Builder.

Design note: this module does NOT reimplement ATS scoring. It builds a
plain-text rendition of a ResumeProfile and hands it to the existing,
already-tested local scoring pipeline in backend/resume_review.py
(review_resume / detect_missing_keywords), so the Resume Builder's
"Check ATS Score" button and the standalone "ATS Resume Review" page
always agree on what counts as a good resume. review_resume() is
called with email="" so this never writes to the "Resume Reviews"
sheet - that history is owned by the review page.

Compatibility note: this only reads fields that exist on the CURRENT
backend.resume_store.ResumeProfile (first_name, last_name, email,
education, skills, internships, projects, certificates, achievements,
hobbies). The "Resume Settings" fields added on top of ResumeProfile
(target_role, summary, etc.) are read defensively via getattr(..., "")
so this file keeps working, unmodified, regardless of which
ResumeProfile snapshot it's imported against.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.resume_store import ResumeProfile
from backend.resume_review import review_resume, ResumeReviewResult, detect_missing_keywords
from backend.logger_setup import get_logger

logger = get_logger(__name__)


def profile_to_plain_text(profile: ResumeProfile) -> str:
    """Render a ResumeProfile as plain text, mirroring the sections a
    real resume file would contain, for local ATS/keyword analysis."""
    lines: list[str] = [profile.full_name or "", profile.email or ""]

    # Read defensively: these fields may or may not exist depending on
    # which ResumeProfile snapshot this module is imported against -
    # getattr keeps this module correct either way, with no edit needed.
    target_role = getattr(profile, "target_role", "") or ""
    summary = getattr(profile, "summary", "") or ""

    if target_role:
        lines.append(target_role)
    if summary:
        lines.append("Summary")
        lines.append(summary)

    if profile.education:
        lines.append("Education")
        lines.append(profile.education)

    if profile.skills:
        lines.append("Skills")
        lines.append(", ".join(profile.skills))

    if profile.internships:
        lines.append("Experience")
        for i in profile.internships:
            lines.append(f"{i.role} - {i.company} ({i.duration})")
            if i.description:
                lines.append(f"- {i.description}")

    if profile.projects:
        lines.append("Projects")
        for p in profile.projects:
            lines.append(f"{p.title} ({p.tech_stack})")
            if p.description:
                lines.append(f"- {p.description}")

    if profile.certificates:
        lines.append("Certifications")
        for c in profile.certificates:
            lines.append(f"{c.name} - {c.issuer} ({c.year})")

    if profile.achievements:
        lines.append("Achievements")
        lines.append(profile.achievements)

    if profile.hobbies:
        lines.append("Hobbies")
        lines.append(", ".join(profile.hobbies))

    return "\n".join(l for l in lines if l and l.strip())


def check_ats_score(profile: ResumeProfile) -> ResumeReviewResult:
    """Run the local ATS review pipeline against this profile's content."""
    text = profile_to_plain_text(profile)
    return review_resume(text, email="")


def suggest_keywords(profile: ResumeProfile, limit: int = 10) -> list[str]:
    """Return up to `limit` commonly-searched keywords missing from the resume."""
    text = profile_to_plain_text(profile)
    _found, missing = detect_missing_keywords(text)
    return missing[:limit]


@dataclass
class CompletenessResult:
    percent: int
    filled: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


_COMPLETENESS_CHECKS: list[tuple[str, str]] = [
    ("Personal details", "_personal"),
    ("Education", "education"),
    ("Skills", "skills"),
    ("Experience / internships", "internships"),
    ("Projects", "projects"),
    ("Certificates", "certificates"),
    ("Achievements", "achievements"),
    ("Hobbies", "hobbies"),
]


def resume_completeness(profile: ResumeProfile) -> CompletenessResult:
    """A simple 0-100% completeness meter across the resume's sections."""
    filled, missing = [], []
    for label, attr in _COMPLETENESS_CHECKS:
        if attr == "_personal":
            ok = bool(profile.first_name and profile.last_name and profile.email)
        else:
            ok = bool(getattr(profile, attr, None))
        (filled if ok else missing).append(label)

    percent = round(100 * len(filled) / len(_COMPLETENESS_CHECKS))
    return CompletenessResult(percent=percent, filled=filled, missing=missing)


def find_duplicate_skills(skills: list[str]) -> list[str]:
    """Return skills that appear more than once, case/whitespace-insensitively."""
    seen: dict[str, int] = {}
    for s in skills:
        key = s.strip().lower()
        if not key:
            continue
        seen[key] = seen.get(key, 0) + 1
    return [k for k, count in seen.items() if count > 1]
