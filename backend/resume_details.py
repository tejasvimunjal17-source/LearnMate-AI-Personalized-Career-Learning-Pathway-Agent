"""
backend/resume_details.py
-----------------------------
Low-level Supabase access for the `resume_details` table. No Google
Sheets and no local CSV/JSON fallback anywhere in this module — if
Supabase is unreachable, callers get a clear ResumeDetailsError instead
of a silent write to disk. This is the deliberate difference from
backend/supabase_client.py (used by the older Sheets-shaped modules),
which still falls back to local JSON so those modules keep working
offline; resume_details.py exists specifically to NOT do that, per this
phase's requirement to remove the Sheets/CSV dependency entirely for
resume storage.

backend/resume_store.py (the domain layer: dataclasses + validation)
calls into this module for all actual persistence. Nothing else should
import this module directly.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.supabase_client import _get_client, SupabaseUnavailableError
from backend.logger_setup import get_logger

logger = get_logger(__name__)

TABLE = "resume_details"


class ResumeDetailsError(RuntimeError):
    """Raised when a resume_details read/write against Supabase fails."""


def resolve_user_id(email: str) -> str:
    """Look up users.id for this email. Raises ResumeDetailsError if not found
    or if Supabase can't be reached."""
    email_norm = (email or "").strip().lower()
    if not email_norm:
        raise ResumeDetailsError("A non-empty email is required to resolve a user.")

    try:
        client = _get_client()
        resp = client.table("users").select("id").eq("email", email_norm).limit(1).execute()
    except SupabaseUnavailableError as exc:
        raise ResumeDetailsError(f"Supabase is not configured/reachable: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to resolve user_id for %s", email_norm)
        raise ResumeDetailsError(f"Could not look up user: {exc}") from exc

    rows = resp.data or []
    if not rows:
        raise ResumeDetailsError(
            f"No registered user found for email '{email_norm}'. Register/login before saving a resume."
        )
    return rows[0]["id"]


def insert_resume_details(payload: dict[str, Any]) -> dict[str, Any]:
    """Insert one new row into resume_details. `payload` must already be in
    DB column shape (see backend.resume_store._to_db_payload). Returns the
    inserted row."""
    try:
        client = _get_client()
        resp = client.table(TABLE).insert(payload).execute()
    except SupabaseUnavailableError as exc:
        raise ResumeDetailsError(f"Supabase is not configured/reachable: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to insert resume_details row")
        raise ResumeDetailsError(f"Could not save resume: {exc}") from exc

    rows = resp.data or []
    if not rows:
        raise ResumeDetailsError("Insert into resume_details returned no row.")
    return rows[0]


def get_latest_for_user(user_id: str) -> dict[str, Any] | None:
    """Return the most recently updated resume_details row for this user, or None."""
    try:
        client = _get_client()
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
    except SupabaseUnavailableError as exc:
        raise ResumeDetailsError(f"Supabase is not configured/reachable: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to read resume_details for user_id=%s", user_id)
        raise ResumeDetailsError(f"Could not read resume record: {exc}") from exc

    rows = resp.data or []
    return rows[0] if rows else None


def update_for_user(user_id: str, payload: dict[str, Any]) -> bool:
    """Update the most recent resume_details row for this user in place.
    Returns True if a row was updated, False if the user has no resume yet."""
    payload = {**payload, "updated_at": datetime.now(timezone.utc).isoformat()}
    try:
        client = _get_client()
        resp = client.table(TABLE).update(payload).eq("user_id", user_id).execute()
    except SupabaseUnavailableError as exc:
        raise ResumeDetailsError(f"Supabase is not configured/reachable: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to update resume_details for user_id=%s", user_id)
        raise ResumeDetailsError(f"Could not update resume: {exc}") from exc

    return bool(resp.data)


def delete_by_id_for_user(resume_id: str, user_id: str) -> bool:
    """Delete one resume_details row, scoped to user_id so a user can only
    ever delete their own saved resumes. Returns True if a row was deleted."""
    try:
        client = _get_client()
        resp = client.table(TABLE).delete().eq("id", resume_id).eq("user_id", user_id).execute()
    except SupabaseUnavailableError as exc:
        raise ResumeDetailsError(f"Supabase is not configured/reachable: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to delete resume_details id=%s for user_id=%s", resume_id, user_id)
        raise ResumeDetailsError(f"Could not delete resume: {exc}") from exc
    return bool(resp.data)
