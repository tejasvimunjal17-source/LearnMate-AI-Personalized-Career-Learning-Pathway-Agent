"""
backend/resume_store.py
-------------------------
Data model and persistence layer for the Resume Builder feature.

As of Phase 4, this module talks directly to Supabase's `resume_details`
table through backend/resume_details.py — there is no Google Sheets and
no local CSV/JSON fallback anywhere in this path. If Supabase is
unreachable, save_resume()/get_latest_resume()/update_resume() raise
ResumeStoreError immediately rather than silently writing to disk.

Every resume is linked to its owner via `user_id` (a foreign key into
`users`, resolved from the caller's email) — resume_details has no email
column of its own.

--- Resume Settings fields (template selection / AI toolkit) ---
first_name/last_name/email/education/skills/certificates/internships/
projects/achievements/hobbies/created_at are unchanged from before.
Seven more fields were added to match the current frontend/resume_builder.py
(template gallery, accent color picker, target role, experience level,
AI-generated summary, one-page toggle, photo toggle):

    template_id, accent_color, target_role, experience_level,
    summary, one_page, show_photo

`template_id` reuses the EXISTING `resume_template` Supabase column from
the earlier Phase 4 migration (sql/003_resume_details_additions.sql) —
the dataclass field is renamed to match frontend/resume_builder.py's and
backend/resume_generator.py's keyword (`template_id=...`), but no
database column was renamed; `resume_template` still exists exactly as
it did, just mapped under a different Python-side name in this file's
serialization layer. accent_color, target_role, experience_level,
summary, one_page, show_photo are genuinely new columns — see
sql/010_resume_settings_additions.sql. `pdf_path`/`docx_path` are also
unchanged from before (still unpopulated, for the same reason documented
below - no durable file storage exists yet).

Public API (save_resume, get_latest_resume, update_resume, _from_db_row,
and the ResumeProfile/ProjectEntry/CertificateEntry/InternshipEntry
dataclasses) keeps the exact names frontend/resume_builder.py,
backend/resume_generator.py, backend/resume_ai.py, backend/resume_ats.py,
and frontend/profile_page.py already import.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

from backend.resume_details import (
    resolve_user_id,
    insert_resume_details,
    get_latest_for_user,
    update_for_user,
    ResumeDetailsError,
)
from backend.logger_setup import get_logger

logger = get_logger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_VALID_EXPERIENCE_LEVELS = ("Fresher", "Entry Level", "Mid Level", "Senior", "Lead / Manager")
_DEFAULT_ACCENT_COLOR = "#2563EB"
_DEFAULT_TEMPLATE_ID = "classic_pro"


class ResumeStoreError(RuntimeError):
    """Raised when a resume record fails validation or cannot be persisted."""


@dataclass
class ProjectEntry:
    title: str = ""
    description: str = ""
    tech_stack: str = ""


@dataclass
class CertificateEntry:
    name: str = ""
    issuer: str = ""
    year: str = ""


@dataclass
class InternshipEntry:
    """A work/internship experience entry (maps to the "Experience" section
    of a generated resume)."""
    role: str = ""
    company: str = ""
    duration: str = ""
    description: str = ""


@dataclass
class ResumeProfile:
    """A user's resume details, as captured by the Resume Builder form.

    `email` is the lookup key used to resolve the owning user_id in
    Supabase - required for every save/update, but never stored as a
    column on resume_details itself (that table has no email column;
    ownership is expressed purely via the user_id foreign key).

    pdf_path / docx_path default to empty string and stay that way:
    backend/resume_generator.py produces in-memory bytes for direct
    download rather than writing to a durable path anywhere, so these
    fields are honestly left blank rather than filled with a fabricated
    value. See sql/003_resume_details_additions.sql for the original
    note on this.
    """
    first_name: str
    last_name: str
    email: str
    education: str = ""
    skills: list[str] = field(default_factory=list)
    certificates: list[CertificateEntry] = field(default_factory=list)
    internships: list[InternshipEntry] = field(default_factory=list)  # = "Experience"
    projects: list[ProjectEntry] = field(default_factory=list)
    achievements: str = ""
    hobbies: list[str] = field(default_factory=list)
    created_at: str = ""
    pdf_path: str = ""
    docx_path: str = ""
    # --- Resume Settings (template gallery / AI toolkit) ---
    template_id: str = _DEFAULT_TEMPLATE_ID
    accent_color: str = _DEFAULT_ACCENT_COLOR
    target_role: str = ""
    experience_level: str = "Fresher"
    summary: str = ""
    one_page: bool = True
    show_photo: bool = False

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------
def _validate_profile(profile: ResumeProfile) -> None:
    """Raise ResumeStoreError if required fields are missing or malformed."""
    if not isinstance(profile, ResumeProfile):
        raise ResumeStoreError(f"Expected a ResumeProfile instance, got {type(profile).__name__}.")
    if not profile.first_name or not profile.first_name.strip():
        raise ResumeStoreError("first_name is required.")
    if not profile.last_name or not profile.last_name.strip():
        raise ResumeStoreError("last_name is required.")
    if not profile.email or not profile.email.strip():
        raise ResumeStoreError("email is required.")
    if not _EMAIL_RE.match(profile.email.strip()):
        raise ResumeStoreError(f"'{profile.email}' is not a valid email address.")


def _validate_email(email: str) -> str:
    if not email or not isinstance(email, str) or not email.strip():
        raise ResumeStoreError("A non-empty email is required.")
    email = email.strip()
    if not _EMAIL_RE.match(email):
        raise ResumeStoreError(f"'{email}' is not a valid email address.")
    return email


# ------------------------------------------------------------------
# Serialization: ResumeProfile <-> resume_details DB row shape
#
# Column mapping note: profile.template_id <-> db column "resume_template"
# (existing column, Phase 4 migration 003) - every other field below maps
# 1:1 by name, including the six genuinely new columns from migration 010
# (accent_color, target_role, experience_level, summary, one_page,
# show_photo).
# ------------------------------------------------------------------
def _to_db_payload(profile: ResumeProfile, user_id: str) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "first_name": profile.first_name.strip(),
        "last_name": profile.last_name.strip(),
        "education": profile.education,
        "skills": list(profile.skills),
        "certificates": [asdict(c) for c in profile.certificates],
        "internships": [asdict(i) for i in profile.internships],
        "projects": [asdict(p) for p in profile.projects],
        "achievements": profile.achievements,
        "hobbies": list(profile.hobbies),
        "pdf_path": profile.pdf_path,
        "docx_path": profile.docx_path,
        "resume_template": profile.template_id or _DEFAULT_TEMPLATE_ID,
        "accent_color": profile.accent_color or _DEFAULT_ACCENT_COLOR,
        "target_role": profile.target_role,
        "experience_level": profile.experience_level or "Fresher",
        "summary": profile.summary,
        "one_page": bool(profile.one_page),
        "show_photo": bool(profile.show_photo),
    }


def _from_db_row(row: dict[str, Any], email: str) -> ResumeProfile:
    def _as_list(value: Any) -> list[str]:
        return list(value) if isinstance(value, list) else []

    def _as_entries(value: Any, cls):
        items = value if isinstance(value, list) else []
        return [cls(**item) for item in items]

    return ResumeProfile(
        first_name=row.get("first_name", ""),
        last_name=row.get("last_name", ""),
        email=email,
        education=row.get("education", ""),
        skills=_as_list(row.get("skills")),
        certificates=_as_entries(row.get("certificates"), CertificateEntry),
        internships=_as_entries(row.get("internships"), InternshipEntry),
        projects=_as_entries(row.get("projects"), ProjectEntry),
        achievements=row.get("achievements", ""),
        hobbies=_as_list(row.get("hobbies")),
        pdf_path=row.get("pdf_path", "") or "",
        docx_path=row.get("docx_path", "") or "",
        created_at=row.get("created_at", "") or "",
        template_id=row.get("resume_template") or _DEFAULT_TEMPLATE_ID,
        accent_color=row.get("accent_color") or _DEFAULT_ACCENT_COLOR,
        target_role=row.get("target_role", "") or "",
        experience_level=row.get("experience_level") or "Fresher",
        summary=row.get("summary", "") or "",
        one_page=bool(row.get("one_page", True)) if row.get("one_page") is not None else True,
        show_photo=bool(row.get("show_photo", False)) if row.get("show_photo") is not None else False,
    )


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------
def save_resume(profile: ResumeProfile) -> None:
    """Validate and insert a new resume record into Supabase, linked to the
    authenticated user via user_id.

    Raises:
        ResumeStoreError: if `profile` fails validation, the user isn't
            registered, or Supabase can't be reached.
    """
    _validate_profile(profile)
    if not profile.created_at:
        profile.created_at = datetime.now(timezone.utc).isoformat()

    try:
        user_id = resolve_user_id(profile.email)
        payload = _to_db_payload(profile, user_id)
        insert_resume_details(payload)
    except ResumeDetailsError as exc:
        logger.exception("Failed to save resume for %s", profile.email)
        raise ResumeStoreError(str(exc)) from exc

    logger.info("Resume saved for %s (template=%s)", profile.email, profile.template_id)


def get_latest_resume(email: str) -> ResumeProfile | None:
    """Return the most recently saved resume for this email, or None if none exists.

    Raises:
        ResumeStoreError: if `email` is missing/invalid, or Supabase can't be reached.
    """
    email = _validate_email(email)

    try:
        user_id = resolve_user_id(email)
        row = get_latest_for_user(user_id)
    except ResumeDetailsError as exc:
        logger.exception("Failed to read resume for %s", email)
        raise ResumeStoreError(str(exc)) from exc

    if row is None:
        return None
    return _from_db_row(row, email)


def update_resume(email: str, profile: ResumeProfile) -> bool:
    """Update this user's existing resume record in place.

    Returns:
        True if a matching row was found and updated, False otherwise.

    Raises:
        ResumeStoreError: if `email`/`profile` fail validation, or the update fails.
    """
    email = _validate_email(email)
    _validate_profile(profile)

    if profile.email.strip() != email:
        raise ResumeStoreError(
            f"Email mismatch: update_resume() called with '{email}' but "
            f"profile.email is '{profile.email}'."
        )

    if not profile.created_at:
        profile.created_at = datetime.now(timezone.utc).isoformat()

    try:
        user_id = resolve_user_id(email)
        payload = _to_db_payload(profile, user_id)
        payload.pop("user_id", None)  # never overwrite the FK on update
        updated = update_for_user(user_id, payload)
    except ResumeDetailsError as exc:
        logger.exception("Failed to update resume for %s", email)
        raise ResumeStoreError(str(exc)) from exc

    if updated:
        logger.info("Resume updated for %s", email)
    else:
        logger.info("No existing resume found to update for %s", email)
    return updated
