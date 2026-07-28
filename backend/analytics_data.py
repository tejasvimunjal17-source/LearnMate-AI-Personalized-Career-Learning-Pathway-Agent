"""
backend/analytics_data.py
------------------------------
Data layer for the Advanced Analytics Dashboard (Phase 4, Part 2).
Every function queries Supabase directly (same _get_client() as every
other Phase 4 module) - no Google Sheets, no CSV/local fallback, no
fabricated numbers. Empty/sparse results (e.g. before activity logging
had anywhere to write to) are returned as empty lists/zero counts, never
invented.

Sources used, all pre-existing tables (no new tables needed for this
module - see sql/001_init_schema.sql for the base schema):
    users                - registrations, DAU/WAU/MAU base
    login_logs           - login trend, active-user windows
    user_activity_logs   - every logged action (both user_id and admin_id
                            branches - the same table backs both "User
                            Activity Logs" and "Admin Audit Logs")
    resume_details        - resume statistics
    resume_reviews         - resume review statistics
    roadmaps               - AI roadmap statistics
    ai_responses            - AI chatbot statistics
    feedback                - feedback statistics
    notifications            - notification statistics
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

from backend.supabase_client import _get_client, SupabaseUnavailableError
from backend.logger_setup import get_logger

logger = get_logger(__name__)


class AnalyticsError(RuntimeError):
    """Raised when an analytics query against Supabase fails."""


def _count(client, table: str, **eq_filters) -> int:
    query = client.table(table).select("id", count="exact")
    for col, val in eq_filters.items():
        query = query.eq(col, val)
    resp = query.execute()
    return resp.count or 0


def _daily_counts(rows: list[dict[str, Any]], date_field: str, days: int) -> list[dict[str, Any]]:
    """Bucket rows into a fixed [today - days + 1, today] daily series,
    filling zero-count days so the chart doesn't have gaps."""
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=days - 1)
    by_day: dict[str, int] = {}
    d = start
    while d <= today:
        by_day[d.isoformat()] = 0
        d += timedelta(days=1)
    for row in rows:
        raw = row.get(date_field, "")
        day = (raw or "")[:10]
        if day in by_day:
            by_day[day] += 1
    return [{"date": d, "count": c} for d, c in by_day.items()]


# ---------------------------------------------------------------------------
# Active users (DAU / WAU / MAU) - based on distinct users with a login_logs
# row in the relevant window. login_logs only started being populated once
# backend/activity_logger.py was wired in (Phase 4 Part 2) - counts will be
# sparse/zero for older sessions, which is accurate, not a bug.
# ---------------------------------------------------------------------------
def _distinct_active_users(client, since: datetime) -> int:
    resp = (
        client.table("login_logs")
        .select("user_id")
        .eq("user_type", "user")
        .gte("login_time", since.isoformat())
        .execute()
    )
    user_ids = {r["user_id"] for r in (resp.data or []) if r.get("user_id")}
    return len(user_ids)


def get_active_user_counts() -> dict[str, int]:
    """Returns {'dau': int, 'wau': int, 'mau': int}."""
    client = _get_client()
    now = datetime.now(timezone.utc)
    return {
        "dau": _distinct_active_users(client, now - timedelta(days=1)),
        "wau": _distinct_active_users(client, now - timedelta(days=7)),
        "mau": _distinct_active_users(client, now - timedelta(days=30)),
    }


# ---------------------------------------------------------------------------
# Registrations / login trends
# ---------------------------------------------------------------------------
def get_total_registrations() -> int:
    client = _get_client()
    return _count(client, "users")


def get_registration_trend(days: int = 14) -> list[dict[str, Any]]:
    client = _get_client()
    since = datetime.now(timezone.utc) - timedelta(days=days - 1)
    resp = client.table("users").select("created_at").gte("created_at", since.isoformat()).execute()
    return _daily_counts(resp.data or [], "created_at", days)


def get_login_trend(days: int = 14) -> list[dict[str, Any]]:
    client = _get_client()
    since = datetime.now(timezone.utc) - timedelta(days=days - 1)
    resp = (
        client.table("login_logs")
        .select("login_time")
        .eq("user_type", "user")
        .gte("login_time", since.isoformat())
        .execute()
    )
    return _daily_counts(resp.data or [], "login_time", days)


# ---------------------------------------------------------------------------
# Feature-specific statistics
# ---------------------------------------------------------------------------
def get_resume_stats() -> dict[str, Any]:
    client = _get_client()
    total_saved = _count(client, "resume_details")
    gen_count = _count(client, "user_activity_logs", activity_type="resume_generation")
    dl_count = _count(client, "user_activity_logs", activity_type="resume_download")
    return {"total_saved": total_saved, "generation_events": gen_count, "download_events": dl_count}


def get_resume_review_stats() -> dict[str, Any]:
    client = _get_client()
    total_reviews = _count(client, "resume_reviews")
    scores_resp = client.table("resume_reviews").select("score").execute()
    scores = [r["score"] for r in (scores_resp.data or []) if r.get("score") is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else None
    return {"total_reviews": total_reviews, "average_score": avg_score}


def get_ai_roadmap_stats() -> dict[str, Any]:
    client = _get_client()
    total_roadmaps = _count(client, "roadmaps")
    gen_events = _count(client, "user_activity_logs", activity_type="ai_roadmap_generation")
    return {"total_roadmaps": total_roadmaps, "generation_events": gen_events}


def get_ai_chatbot_stats() -> dict[str, Any]:
    client = _get_client()
    total_exchanges = _count(client, "ai_responses")
    usage_events = _count(client, "user_activity_logs", activity_type="ai_chatbot_usage")
    return {"total_exchanges": total_exchanges, "usage_events": usage_events}


def get_feedback_stats() -> dict[str, Any]:
    client = _get_client()
    resp = client.table("feedback").select("status, category, rating").execute()
    rows = resp.data or []
    total = len(rows)
    by_status: dict[str, int] = {}
    by_category: dict[str, int] = {}
    ratings = []
    for r in rows:
        status = r.get("status") or "pending"
        category = r.get("category") or "general"
        by_status[status] = by_status.get(status, 0) + 1
        by_category[category] = by_category.get(category, 0) + 1
        if r.get("rating") is not None:
            ratings.append(r["rating"])
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
    return {"total": total, "by_status": by_status, "by_category": by_category, "average_rating": avg_rating}


def get_notification_stats() -> dict[str, Any]:
    client = _get_client()
    total = _count(client, "notifications")
    broadcast = _count(client, "notifications", type="broadcast")
    direct = _count(client, "notifications", type="direct")
    active = _count(client, "notifications", is_active=True)
    reads_resp = client.table("notification_reads").select("id", count="exact").execute()
    total_reads = reads_resp.count or 0
    return {
        "total": total, "broadcast": broadcast, "direct": direct,
        "active": active, "total_reads": total_reads,
    }


# ---------------------------------------------------------------------------
# Activity-log-derived views: most active users, recent activity, admin
# audit summary. All three read straight from user_activity_logs.
# ---------------------------------------------------------------------------
def get_most_active_users(limit: int = 10) -> list[dict[str, Any]]:
    """Top users by number of logged activities (all-time)."""
    client = _get_client()
    resp = (
        client.table("user_activity_logs")
        .select("user_id, users(email, first_name, last_name)")
        .not_.is_("user_id", "null")
        .execute()
    )
    rows = resp.data or []
    counts: dict[str, dict[str, Any]] = {}
    for r in rows:
        uid = r.get("user_id")
        if not uid:
            continue
        if uid not in counts:
            u = r.get("users") or {}
            counts[uid] = {
                "user_id": uid,
                "email": u.get("email", "") if isinstance(u, dict) else "",
                "name": f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() if isinstance(u, dict) else "",
                "activity_count": 0,
            }
        counts[uid]["activity_count"] += 1
    ranked = sorted(counts.values(), key=lambda x: x["activity_count"], reverse=True)
    return ranked[:limit]


def get_recent_activity(limit: int = 20) -> list[dict[str, Any]]:
    """Most recent user-side activity events, newest first."""
    client = _get_client()
    resp = (
        client.table("user_activity_logs")
        .select("activity_type, activity_detail, created_at, users(email)")
        .not_.is_("user_id", "null")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return resp.data or []


def get_admin_activity_summary(limit: int = 20) -> dict[str, Any]:
    """The Admin Audit Log: recent admin actions + a per-action-type count."""
    client = _get_client()
    resp = (
        client.table("user_activity_logs")
        .select("activity_type, activity_detail, created_at, admin_users(email)")
        .not_.is_("admin_id", "null")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    recent = resp.data or []

    all_resp = client.table("user_activity_logs").select("activity_type").not_.is_("admin_id", "null").execute()
    by_type: dict[str, int] = {}
    for r in all_resp.data or []:
        t = r.get("activity_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    return {"recent": recent, "by_type": by_type}


# ---------------------------------------------------------------------------
# One-call snapshot for the Analytics page
# ---------------------------------------------------------------------------
@dataclass
class AnalyticsSnapshot:
    active_users: dict[str, int] = field(default_factory=dict)
    total_registrations: int = 0
    registration_trend: list[dict[str, Any]] = field(default_factory=list)
    login_trend: list[dict[str, Any]] = field(default_factory=list)
    resume_stats: dict[str, Any] = field(default_factory=dict)
    resume_review_stats: dict[str, Any] = field(default_factory=dict)
    ai_roadmap_stats: dict[str, Any] = field(default_factory=dict)
    ai_chatbot_stats: dict[str, Any] = field(default_factory=dict)
    feedback_stats: dict[str, Any] = field(default_factory=dict)
    notification_stats: dict[str, Any] = field(default_factory=dict)
    most_active_users: list[dict[str, Any]] = field(default_factory=list)
    recent_activity: list[dict[str, Any]] = field(default_factory=list)
    admin_activity: dict[str, Any] = field(default_factory=dict)


def get_analytics_snapshot(trend_days: int = 14) -> AnalyticsSnapshot:
    """Fetch everything the Analytics Dashboard needs in one call.

    Raises:
        AnalyticsError: if Supabase can't be reached. Callers should show
            an honest error rather than a dashboard full of zeros.
    """
    try:
        _get_client()  # fail fast with a clear error if unreachable
        return AnalyticsSnapshot(
            active_users=get_active_user_counts(),
            total_registrations=get_total_registrations(),
            registration_trend=get_registration_trend(trend_days),
            login_trend=get_login_trend(trend_days),
            resume_stats=get_resume_stats(),
            resume_review_stats=get_resume_review_stats(),
            ai_roadmap_stats=get_ai_roadmap_stats(),
            ai_chatbot_stats=get_ai_chatbot_stats(),
            feedback_stats=get_feedback_stats(),
            notification_stats=get_notification_stats(),
            most_active_users=get_most_active_users(),
            recent_activity=get_recent_activity(),
            admin_activity=get_admin_activity_summary(),
        )
    except SupabaseUnavailableError as exc:
        raise AnalyticsError(f"Supabase is not configured/reachable: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to build analytics snapshot")
        raise AnalyticsError(f"Could not load analytics: {exc}") from exc
