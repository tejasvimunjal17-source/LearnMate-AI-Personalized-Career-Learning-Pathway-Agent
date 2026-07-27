"""
backend/resume_store.py
-------------------------
Data model and persistence layer for the Resume Builder feature.

Follows the same architecture as backend/responses_store.py: a typed
dataclass model, validation before any write, and all Google Sheets I/O
delegated to backend/sheets_client.py (which is itself Sheets-first with
an automatic local-CSV fallback - callers here never need to know which
backend is actually active).

Sheet: "Users Resume Details"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

from config import SHEETS_CONFIG
from backend.sheets_client import append_row, read_rows, update_row
from backend.logger_setup import get_logger

logger = get_logger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# config.py does not currently define a dedicated sheet-name field for the
# resume-builder sheet (unlike users_sheet_name / responses_sheet_name /
# resume_review_sheet_name). We read it defensively via getattr so this
# module still honors "reuse config.py for sheet names" if/when that field
# is added, without requiring a config.py edit right now and without
# crashing if it's absent.
RESUME_SHEET_NAME: str = getattr(SHEETS_CONFIG, "resume_sheet_name", "Users Resume Details")


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
    role: str = ""
    company: str = ""
    duration: str = ""
    description: str = ""


@dataclass
class ResumeProfile:
    """A user's resume details, as captured by the Resume Builder form.

    Note: `email` is included in addition to the fields explicitly
    requested (first_name, last_name, education, skills, certificates,
    internships, projects, achievements, hobbies, created_at) because it
    is the required lookup key for get_latest_resume()/update_resume()
    and for the "email" column in the "Users Resume Details" sheet -
    without it, a saved resume could never be retrieved or updated.

    The fields below `created_at` (template_id through show_photo) are
    an additive "Resume Settings" extension for the template gallery /
    AI toolkit. They all have safe defaults, are appended to the END of
    the sheet header (never inserted in the middle), and _from_row()
    reads them with .get(..., default) - so existing rows saved before
    this change still load correctly, and no existing field, column
    position, or caller is touched.
    """
    first_name: str
    last_name: str
    email: str
    education: str = ""
    skills: list[str] = field(default_factory=list)
    certificates: list[CertificateEntry] = field(default_factory=list)
    internships: list[InternshipEntry] = field(default_factory=list)
    projects: list[ProjectEntry] = field(default_factory=list)
    achievements: str = ""
    hobbies: list[str] = field(default_factory=list)
    created_at: str = ""
    # --- Resume Settings (additive) ---
    template_id: str = "classic_pro"
    accent_color: str = "#2563EB"
    target_role: str = ""
    experience_level: str = "Fresher"
    summary: str = ""
    one_page: bool = True
    show_photo: bool = False

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


# Column order for the "Users Resume Details" sheet. New columns are
# appended at the end so existing sheet rows/data are never shifted.
RESUME_SHEET_HEADER: list[str] = [
    "email", "first_name", "last_name", "education", "skills",
    "certificates_json", "internships_json", "projects_json",
    "achievements", "hobbies", "created_at",
    "template_id", "accent_color", "target_role", "experience_level",
    "summary", "one_page", "show_photo",
]


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
# Serialization helpers
# ------------------------------------------------------------------
def _to_row(profile: ResumeProfile) -> dict[str, Any]:
    import json

    return {
        "email": profile.email.strip(),
        "first_name": profile.first_name.strip(),
        "last_name": profile.last_name.strip(),
        "education": profile.education,
        "skills": ", ".join(profile.skills),
        "certificates_json": json.dumps([asdict(c) for c in profile.certificates]),
        "internships_json": json.dumps([asdict(i) for i in profile.internships]),
        "projects_json": json.dumps([asdict(p) for p in profile.projects]),
        "achievements": profile.achievements,
        "hobbies": ", ".join(profile.hobbies),
        "created_at": profile.created_at or datetime.now(timezone.utc).isoformat(),
        "template_id": profile.template_id or "classic_pro",
        "accent_color": profile.accent_color or "#2563EB",
        "target_role": profile.target_role,
        "experience_level": profile.experience_level or "Fresher",
        "summary": profile.summary,
        "one_page": "true" if profile.one_page else "false",
        "show_photo": "true" if profile.show_photo else "false",
    }


def _from_row(row: dict[str, Any]) -> ResumeProfile:
    import json

    def _split(value: str) -> list[str]:
        return [v.strip() for v in value.split(",") if v.strip()] if value else []

    def _load_list(value: str, cls):
        try:
            items = json.loads(value) if value else []
        except (json.JSONDecodeError, TypeError):
            items = []
        return [cls(**item) for item in items]

    return ResumeProfile(
        first_name=row.get("first_name", ""),
        last_name=row.get("last_name", ""),
        email=row.get("email", ""),
        education=row.get("education", ""),
        skills=_split(row.get("skills", "")),
        certificates=_load_list(row.get("certificates_json", ""), CertificateEntry),
        internships=_load_list(row.get("internships_json", ""), InternshipEntry),
        projects=_load_list(row.get("projects_json", ""), ProjectEntry),
        achievements=row.get("achievements", ""),
        hobbies=_split(row.get("hobbies", "")),
        created_at=row.get("created_at", ""),
        template_id=row.get("template_id") or "classic_pro",
        accent_color=row.get("accent_color") or "#2563EB",
        target_role=row.get("target_role", ""),
        experience_level=row.get("experience_level") or "Fresher",
        summary=row.get("summary", ""),
        one_page=str(row.get("one_page", "true")).strip().lower() != "false",
        show_photo=str(row.get("show_photo", "false")).strip().lower() == "true",
    )


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------
def save_resume(profile: ResumeProfile) -> None:
    """Validate and append a new resume record to the 'Users Resume Details' sheet.

    Raises:
        ResumeStoreError: if `profile` fails validation.
    """
    _validate_profile(profile)
    if not profile.created_at:
        profile.created_at = datetime.now(timezone.utc).isoformat()

    row = _to_row(profile)
    try:
        append_row(RESUME_SHEET_NAME, RESUME_SHEET_HEADER, row)
    except Exception as exc:  # noqa: BLE001 - surface as a domain-specific error
        logger.exception("Failed to save resume for %s", profile.email)
        raise ResumeStoreError(f"Could not save resume: {exc}") from exc

    logger.info("Resume saved for %s", profile.email)


def get_latest_resume(email: str) -> ResumeProfile | None:
    """Return the most recently saved resume for this email, or None if none exists.

    Raises:
        ResumeStoreError: if `email` is missing/invalid, or the sheet can't be read.
    """
    email = _validate_email(email)

    try:
        rows = read_rows(RESUME_SHEET_NAME, RESUME_SHEET_HEADER)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to read resumes while looking up %s", email)
        raise ResumeStoreError(f"Could not read resume records: {exc}") from exc

    matches = [r for r in rows if r.get("email") == email]
    if not matches:
        return None

    # Rows are appended in write order, so the last match is the most recent.
    # If created_at is populated and sortable, prefer that as the tiebreaker.
    try:
        matches.sort(key=lambda r: r.get("created_at", ""))
    except TypeError:
        pass
    return _from_row(matches[-1])


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

    row = _to_row(profile)
    try:
        updated = update_row(
            RESUME_SHEET_NAME, RESUME_SHEET_HEADER,
            match_col="email", match_value=email, updates=row,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to update resume for %s", email)
        raise ResumeStoreError(f"Could not update resume: {exc}") from exc

    if updated:
        logger.info("Resume updated for %s", email)
    else:
        logger.info("No existing resume found to update for %s", email)
    return updated