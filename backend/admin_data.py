"""
backend/admin_data.py
------------------------
Data-access layer for the Admin Panel (Phase 3). Everything here talks to
Supabase directly through the same underlying client as
backend/supabase_client.py and backend/admin_auth.py (service-role key,
backend-only, RLS-bypassing by design).

This module is intentionally separate from backend/supabase_client.py:
that module's job is to keep the four *existing* Sheets-shaped store
modules (auth.py, resume_store.py, resume_review.py, responses_store.py)
working unchanged. This module is new, admin-only, and free to talk to
Supabase in a more natural, relational way (joins, aggregates, real
pagination) since there is no legacy caller shape to preserve here.

All functions return either plain dicts/lists or pandas DataFrames -
never fabricated data. If a table is empty, callers get an empty
list/DataFrame and the UI is expected to show an honest empty state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any

import pandas as pd

from backend.supabase_client import _get_client, SupabaseUnavailableError
from backend.logger_setup import get_logger

logger = get_logger(__name__)


class AdminDataError(RuntimeError):
    """Raised when an admin data operation fails against Supabase."""


# ---------------------------------------------------------------------------
# Database Explorer table registry
# Maps a human-readable tab label -> (table name, select clause, columns to
# flatten from an embedded relation). Used by both the Database Explorer and
# (for the 3 shared ones) other admin pages.
# ---------------------------------------------------------------------------
DB_TABLES: dict[str, dict[str, Any]] = {
    "Users Data": {
        "table": "users",
        "select": "*",
        "flatten": {},
    },
    "Resume Details": {
        "table": "resume_details",
        "select": "*, users(email)",
        "flatten": {"users": ["email"]},
    },
    "Resume Reviews": {
        "table": "resume_reviews",
        "select": "*, users(email)",
        "flatten": {"users": ["email"]},
    },
    "Roadmap Requests": {
        "table": "roadmap_requests",
        "select": "*, users(email)",
        "flatten": {"users": ["email"]},
    },
    "Generated Roadmaps": {
        "table": "roadmaps",
        "select": "*, users(email)",
        "flatten": {"users": ["email"]},
    },
    "AI Responses": {
        "table": "ai_responses",
        "select": "*, users(email)",
        "flatten": {"users": ["email"]},
    },
    "Feedback": {
        "table": "feedback",
        "select": "*, users(email)",
        "flatten": {"users": ["email"]},
    },
    "Login Logs": {
        "table": "login_logs",
        "select": "*, users(email), admin_users(email)",
        "flatten": {"users": ["email"], "admin_users": ["email"]},
    },
    "User Activity Logs": {
        "table": "user_activity_logs",
        "select": "*, users(email), admin_users(email)",
        "flatten": {"users": ["email"], "admin_users": ["email"]},
    },
    "Announcements": {
        "table": "announcements",
        "select": "*, admin_users(email)",
        "flatten": {"admin_users": ["email"]},
    },
}


def _flatten(rows: list[dict[str, Any]], flatten_map: dict[str, list[str]]) -> list[dict[str, Any]]:
    """Pull fields out of embedded relation dicts (e.g. row['users']['email'])
    into top-level columns (e.g. row['users.email']), and drop the nested dict."""
    out = []
    for row in rows:
        flat = dict(row)
        for relation, fields in flatten_map.items():
            nested = flat.pop(relation, None) or {}
            for f in fields:
                flat[f"{relation}.{f}"] = nested.get(f, "") if isinstance(nested, dict) else ""
        out.append(flat)
    return out


def fetch_table_df(tab_label: str) -> pd.DataFrame:
    """Fetch a Database Explorer tab's full contents as a DataFrame.

    Raises AdminDataError if Supabase is unreachable or the label is unknown.
    Returns an empty DataFrame (not an error) if the table simply has no rows.
    """
    spec = DB_TABLES.get(tab_label)
    if spec is None:
        raise AdminDataError(f"Unknown Database Explorer tab: '{tab_label}'")

    try:
        client = _get_client()
        resp = client.table(spec["table"]).select(spec["select"]).execute()
    except SupabaseUnavailableError as exc:
        raise AdminDataError(f"Supabase is not configured/reachable: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to fetch table '%s' for Database Explorer", spec["table"])
        raise AdminDataError(f"Could not read '{tab_label}': {exc}") from exc

    rows = _flatten(resp.data or [], spec["flatten"])
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Dashboard KPIs
# ---------------------------------------------------------------------------
@dataclass
class DashboardStats:
    total_users: int
    active_users: int
    new_users_today: int
    total_resume_details: int
    total_resume_reviews: int
    average_ats_score: float | None
    total_roadmap_requests: int
    total_generated_roadmaps: int
    total_ai_responses: int
    total_feedback: int
    recent_registrations: list[dict[str, Any]]
    signups_last_14_days: list[dict[str, Any]]  # [{date, count}], for a chart


def _count(client, table: str, **eq_filters) -> int:
    query = client.table(table).select("id", count="exact")
    for col, val in eq_filters.items():
        query = query.eq(col, val)
    resp = query.execute()
    return resp.count or 0


def get_dashboard_stats() -> DashboardStats:
    """Compute all Admin Dashboard KPIs from live Supabase data.

    Never fabricates numbers: if Supabase is unreachable, raises
    AdminDataError so the UI can show an honest error instead of zeros.
    """
    try:
        client = _get_client()
    except SupabaseUnavailableError as exc:
        raise AdminDataError(f"Supabase is not configured/reachable: {exc}") from exc

    try:
        total_users = _count(client, "users")
        active_users = _count(client, "users", is_active=True)

        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        new_today_resp = (
            client.table("users").select("id", count="exact").gte("created_at", today_start.isoformat()).execute()
        )
        new_users_today = new_today_resp.count or 0

        total_resume_details = _count(client, "resume_details")
        total_resume_reviews = _count(client, "resume_reviews")
        total_roadmap_requests = _count(client, "roadmap_requests")
        total_generated_roadmaps = _count(client, "roadmaps")
        total_ai_responses = _count(client, "ai_responses")
        total_feedback = _count(client, "feedback")

        scores_resp = client.table("resume_reviews").select("score").execute()
        scores = [r["score"] for r in (scores_resp.data or []) if r.get("score") is not None]
        average_ats_score = round(sum(scores) / len(scores), 1) if scores else None

        recent_resp = (
            client.table("users")
            .select("first_name, last_name, email, created_at")
            .order("created_at", desc=True)
            .limit(8)
            .execute()
        )
        recent_registrations = recent_resp.data or []

        window_start = today_start - timedelta(days=13)
        window_resp = (
            client.table("users")
            .select("created_at")
            .gte("created_at", window_start.isoformat())
            .execute()
        )
        by_day: dict[str, int] = {}
        for i in range(14):
            day = (window_start + timedelta(days=i)).strftime("%Y-%m-%d")
            by_day[day] = 0
        for row in window_resp.data or []:
            day = (row.get("created_at") or "")[:10]
            if day in by_day:
                by_day[day] += 1
        signups_last_14_days = [{"date": d, "count": c} for d, c in by_day.items()]

    except AdminDataError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to compute dashboard stats")
        raise AdminDataError(f"Could not compute dashboard stats: {exc}") from exc

    return DashboardStats(
        total_users=total_users,
        active_users=active_users,
        new_users_today=new_users_today,
        total_resume_details=total_resume_details,
        total_resume_reviews=total_resume_reviews,
        average_ats_score=average_ats_score,
        total_roadmap_requests=total_roadmap_requests,
        total_generated_roadmaps=total_generated_roadmaps,
        total_ai_responses=total_ai_responses,
        total_feedback=total_feedback,
        recent_registrations=recent_registrations,
        signups_last_14_days=signups_last_14_days,
    )


# ---------------------------------------------------------------------------
# User Management
# ---------------------------------------------------------------------------
def list_users() -> pd.DataFrame:
    client = _get_client()
    resp = client.table("users").select("*").order("created_at", desc=True).execute()
    return pd.DataFrame(resp.data or [])


def set_user_active(user_id: str, is_active: bool) -> None:
    client = _get_client()
    client.table("users").update(
        {"is_active": is_active, "updated_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", user_id).execute()
    logger.info("User %s set to is_active=%s by admin", user_id, is_active)


def get_user_roadmap_history(user_id: str) -> pd.DataFrame:
    client = _get_client()
    resp = (
        client.table("roadmaps")
        .select("id, title, is_offline_fallback, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return pd.DataFrame(resp.data or [])


def get_user_resume_history(user_id: str) -> pd.DataFrame:
    client = _get_client()
    resp = (
        client.table("resume_details")
        .select("id, first_name, last_name, education, created_at, updated_at")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .execute()
    )
    return pd.DataFrame(resp.data or [])


# ---------------------------------------------------------------------------
# Feedback Management
# ---------------------------------------------------------------------------
def update_feedback_status(feedback_id: str, status: str) -> None:
    if status not in ("pending", "reviewed", "resolved"):
        raise AdminDataError(f"Invalid feedback status: '{status}'")
    client = _get_client()
    updates: dict[str, Any] = {"status": status}
    if status == "resolved":
        updates["resolved_at"] = datetime.now(timezone.utc).isoformat()
    client.table("feedback").update(updates).eq("id", feedback_id).execute()
    logger.info("Feedback %s marked as %s", feedback_id, status)


# ---------------------------------------------------------------------------
# Announcement Manager
# ---------------------------------------------------------------------------
def list_announcements() -> pd.DataFrame:
    client = _get_client()
    resp = client.table("announcements").select("*").order("created_at", desc=True).execute()
    return pd.DataFrame(resp.data or [])


def get_active_announcements() -> list[dict[str, Any]]:
    """Used post-login to show active announcements to regular users."""
    client = _get_client()
    resp = (
        client.table("announcements")
        .select("id, title, body, created_at")
        .eq("is_active", True)
        .order("created_at", desc=True)
        .execute()
    )
    return resp.data or []


def create_announcement(title: str, body: str, created_by_admin_id: str) -> None:
    if not title.strip() or not body.strip():
        raise AdminDataError("Announcement title and body are required.")
    client = _get_client()
    client.table("announcements").insert(
        {"title": title.strip(), "body": body.strip(), "created_by": created_by_admin_id, "is_active": True}
    ).execute()


def update_announcement(announcement_id: str, title: str, body: str) -> None:
    if not title.strip() or not body.strip():
        raise AdminDataError("Announcement title and body are required.")
    client = _get_client()
    client.table("announcements").update(
        {"title": title.strip(), "body": body.strip(), "updated_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", announcement_id).execute()


def set_announcement_active(announcement_id: str, is_active: bool) -> None:
    client = _get_client()
    client.table("announcements").update(
        {"is_active": is_active, "updated_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", announcement_id).execute()


def delete_announcement(announcement_id: str) -> None:
    client = _get_client()
    client.table("announcements").delete().eq("id", announcement_id).execute()
    logger.info("Announcement %s deleted by admin", announcement_id)
