"""
backend/roadmap_store.py
----------------------------
Persistence for AI-generated learning roadmaps, into Supabase's
`roadmaps` table. Direct Supabase access, no Sheets/CSV fallback (same
philosophy as backend/resume_details.py and backend/ai_response_store.py
in Phase 4).

Design constraint, matching backend/responses_store.py's existing
convention: saving a roadmap must NEVER block or break roadmap
generation itself. save_generated_roadmap() catches and logs every
failure internally rather than raising, so app.py's existing "generate
-> show success -> balloons" flow is completely unaffected either way.
"""

from __future__ import annotations

from typing import Any, Optional

from backend.roadmap_engine import StudentProfile
from backend.supabase_client import _get_client, SupabaseUnavailableError
from backend.logger_setup import get_logger

logger = get_logger(__name__)

TABLE = "roadmaps"


def _resolve_user_id(client, email: str) -> Optional[str]:
    email_norm = (email or "").strip().lower()
    if not email_norm:
        return None
    resp = client.table("users").select("id").eq("email", email_norm).limit(1).execute()
    rows = resp.data or []
    return rows[0]["id"] if rows else None


def _extract_projects(roadmap: dict[str, Any]) -> list[str]:
    """Pull every project mention out of the roadmap dict: each week's
    mini_project plus the capstone_project, in order."""
    projects: list[str] = []
    for milestone in roadmap.get("weekly_milestones", []) or []:
        mini = milestone.get("mini_project")
        if mini:
            projects.append(mini)
    capstone = roadmap.get("capstone_project")
    if capstone:
        projects.append(capstone)
    return projects


def save_generated_roadmap(email: str, profile: StudentProfile, roadmap: dict[str, Any]) -> None:
    """Persist one AI-generated roadmap. Best-effort: never raises.

    Args:
        email: The authenticated user's email (used to resolve user_id).
        profile: The StudentProfile that produced this roadmap.
        roadmap: The dict returned by backend.roadmap_engine.generate_roadmap()
            (unchanged - includes weekly_milestones, certifications,
            capstone_project, estimated_duration_weeks, _source, etc.).
    """
    try:
        client = _get_client()
    except SupabaseUnavailableError as exc:
        logger.warning("Supabase unavailable - roadmap not persisted for %s: %s", email, exc)
        return

    try:
        user_id = _resolve_user_id(client, email)
        if not user_id:
            logger.warning("No registered user found for '%s' - roadmap not persisted.", email)
            return

        duration_weeks = roadmap.get("estimated_duration_weeks")
        payload: dict[str, Any] = {
            "user_id": user_id,
            "title": f"{profile.career_goal} — {profile.preferred_domain}".strip(" —"),
            "roadmap_json": roadmap,
            "is_offline_fallback": str(roadmap.get("_source", "")).startswith("offline"),
            "career_goal": profile.career_goal,
            "current_skills": list(profile.existing_skills),
            "weekly_roadmap": roadmap.get("weekly_milestones", []),
            "certifications": roadmap.get("certifications", []),
            "projects": _extract_projects(roadmap),
            "estimated_timeline": f"{duration_weeks} weeks" if duration_weeks else "",
        }

        client.table(TABLE).insert(payload).execute()
    except Exception:  # noqa: BLE001 - never block roadmap generation on logging failure
        logger.exception("Failed to persist generated roadmap for %s", email)
        return

    logger.info("Generated roadmap persisted for %s", email)
