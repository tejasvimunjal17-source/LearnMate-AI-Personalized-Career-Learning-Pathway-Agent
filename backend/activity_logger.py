"""
backend/activity_logger.py
------------------------------
Writes to the `login_logs` and `user_activity_logs` tables — both defined
in sql/001_init_schema.sql (Phase 1) but never populated until now. This
module is the missing piece: every call site that represents a loggable
event (login, logout, registration, resume generation, etc.) calls one
of the functions here.

Design constraint, consistent with every other *_store.py in this app:
logging must NEVER break the user-facing action it's attached to.
log_activity() / log_login() / log_logout() all catch and log their own
failures rather than raising - a Supabase hiccup while logging "resume
downloaded" must not stop the download.

Browser/device/IP honesty: Streamlit's st.context.headers (available in
recent Streamlit versions) is the only source for a User-Agent string in
this environment, and even that depends on the hosting platform actually
forwarding headers through to the Streamlit server process - there is no
reliable client IP available at all in a plain Streamlit Cloud deployment
(no request object with the real client IP; a reverse proxy's IP is not
the user's). Rather than fabricate these, _capture_client_context() below
returns None for whichever field it can't genuinely obtain.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from backend.supabase_client import _get_client, SupabaseUnavailableError
from backend.logger_setup import get_logger

logger = get_logger(__name__)

ACTIVITY_TABLE = "user_activity_logs"
LOGIN_TABLE = "login_logs"

# The exact set of activity_type values this app writes - kept as a single
# source of truth so callers and the Analytics Dashboard agree on spelling.
ACTIVITY_TYPES = (
    "login",
    "logout",
    "registration",
    "resume_generation",
    "resume_download",
    "resume_review",
    "ai_roadmap_generation",
    "ai_chatbot_usage",
    "profile_update",
    "feedback_submission",
)


def _resolve_user_id(client, email: str) -> Optional[str]:
    email_norm = (email or "").strip().lower()
    if not email_norm:
        return None
    resp = client.table("users").select("id").eq("email", email_norm).limit(1).execute()
    rows = resp.data or []
    return rows[0]["id"] if rows else None


def _capture_client_context() -> tuple[Optional[str], Optional[str]]:
    """Best-effort (user_agent, ip_address). Returns (None, None) if the
    runtime doesn't expose this - never fabricated."""
    try:
        import streamlit as st

        headers = getattr(st.context, "headers", None) or {}
        user_agent = headers.get("User-Agent") or headers.get("user-agent")
        # There is no trustworthy client IP available in a standard
        # Streamlit deployment without platform-specific proxy
        # configuration - left as None rather than logging a proxy/
        # load-balancer IP that isn't actually the user's.
        return user_agent, None
    except Exception:  # noqa: BLE001 - context capture must never break logging
        return None, None


# ---------------------------------------------------------------------------
# General activity logging (login, logout, registration, resume_generation, ...)
# ---------------------------------------------------------------------------
def log_activity(email: str, activity_type: str, detail: Optional[dict[str, Any]] = None) -> None:
    """Log one user activity event. Best-effort: never raises.

    Args:
        email: The acting user's email.
        activity_type: One of ACTIVITY_TYPES (not enforced strictly here -
            logging must not break over a typo, but callers should use the
            constants).
        detail: Optional small JSON-serializable dict of extra context
            (e.g. {"template": "modern"} for resume_generation).
    """
    try:
        client = _get_client()
    except SupabaseUnavailableError as exc:
        logger.warning("Supabase unavailable - activity '%s' not logged: %s", activity_type, exc)
        return

    try:
        user_id = _resolve_user_id(client, email)
        client.table(ACTIVITY_TABLE).insert(
            {
                "user_id": user_id,
                "admin_id": None,
                "activity_type": activity_type,
                "activity_detail": detail or {},
            }
        ).execute()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to log activity '%s' for %s", activity_type, email)


def log_admin_activity(admin_id: str, activity_type: str, detail: Optional[dict[str, Any]] = None) -> None:
    """Log one admin action (the 'Admin Audit Log'). Best-effort: never raises."""
    if not admin_id:
        return
    try:
        client = _get_client()
        client.table(ACTIVITY_TABLE).insert(
            {
                "user_id": None,
                "admin_id": admin_id,
                "activity_type": activity_type,
                "activity_detail": detail or {},
            }
        ).execute()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to log admin activity '%s' for admin %s", activity_type, admin_id)


# ---------------------------------------------------------------------------
# Login / logout (separate table: login_logs, with login_time/logout_time)
# ---------------------------------------------------------------------------
def log_login(email: str) -> Optional[str]:
    """Record a user login. Returns the new login_logs row id (to pass to
    log_logout later), or None if logging failed or the user wasn't found -
    callers should treat a None return as 'no-op on logout', not an error."""
    try:
        client = _get_client()
        user_agent, ip_address = _capture_client_context()
        user_id = _resolve_user_id(client, email)
        if not user_id:
            return None
        resp = client.table(LOGIN_TABLE).insert(
            {"user_id": user_id, "user_type": "user", "user_agent": user_agent, "ip_address": ip_address}
        ).execute()
        rows = resp.data or []
        return rows[0]["id"] if rows else None
    except Exception:  # noqa: BLE001
        logger.exception("Failed to log login for %s", email)
        return None


def log_admin_login(admin_id: str) -> Optional[str]:
    """Record an admin login. Returns the new login_logs row id, or None."""
    try:
        client = _get_client()
        user_agent, ip_address = _capture_client_context()
        resp = client.table(LOGIN_TABLE).insert(
            {"admin_id": admin_id, "user_type": "admin", "user_agent": user_agent, "ip_address": ip_address}
        ).execute()
        rows = resp.data or []
        return rows[0]["id"] if rows else None
    except Exception:  # noqa: BLE001
        logger.exception("Failed to log admin login for %s", admin_id)
        return None


def log_logout(login_log_id: Optional[str]) -> None:
    """Stamp logout_time on a previously-created login_logs row. No-op if
    login_log_id is None (e.g. the login itself wasn't logged)."""
    if not login_log_id:
        return
    try:
        client = _get_client()
        client.table(LOGIN_TABLE).update(
            {"logout_time": datetime.now(timezone.utc).isoformat()}
        ).eq("id", login_log_id).execute()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to log logout for login_log_id=%s", login_log_id)


# ---------------------------------------------------------------------------
# Resume Downloads History (Phase 4, Part 3) — reads the resume_download
# activity events already written by log_activity() from
# frontend/resume_builder.py and frontend/profile_page.py's download
# buttons. No separate table: a "download" is just an activity_type on
# the same user_activity_logs row every other activity uses.
# ---------------------------------------------------------------------------
def get_resume_download_history(user_id: str) -> list[dict[str, Any]]:
    """Every logged resume_download event for this user, newest first."""
    try:
        client = _get_client()
        resp = (
            client.table(ACTIVITY_TABLE)
            .select("id, activity_detail, created_at")
            .eq("user_id", user_id)
            .eq("activity_type", "resume_download")
            .order("created_at", desc=True)
            .execute()
        )
        return resp.data or []
    except Exception:  # noqa: BLE001
        logger.exception("Failed to load resume_download history for user_id=%s", user_id)
        return []


def delete_activity_log_for_user(log_id: str, user_id: str) -> bool:
    """Delete one user_activity_logs row, scoped to user_id. Raises on a
    genuine Supabase failure - unlike log_activity()'s best-effort write
    convention, a user-initiated delete should surface a real error."""
    try:
        client = _get_client()
        resp = client.table(ACTIVITY_TABLE).delete().eq("id", log_id).eq("user_id", user_id).execute()
    except SupabaseUnavailableError as exc:
        raise RuntimeError(f"Supabase is not configured/reachable: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to delete activity log id=%s for user_id=%s", log_id, user_id)
        raise RuntimeError(f"Could not delete history entry: {exc}") from exc
    return bool(resp.data)
