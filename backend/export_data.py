"""
backend/export_data.py
---------------------------
Data layer for the Admin Export Center (Phase 4, Part 4). Reuses
backend.admin_data.fetch_table_df() / DB_TABLES for the eight raw-table
exports (Users, Resume Details, Resume Reviews, AI Responses, Feedback,
Notifications, Activity Logs), and adds one purpose-built export for
Analytics, which isn't a single table but a flattened snapshot of
backend.analytics_data.get_analytics_snapshot().

Every export is a real Supabase query at request time - there is no
caching layer here to go stale, and nothing is fabricated: an empty
table exports as a header-only CSV/Excel, not a placeholder.
"""

from __future__ import annotations

import pandas as pd

from backend.admin_data import fetch_table_df, AdminDataError
from backend.analytics_data import get_analytics_snapshot, AnalyticsError
from backend.logger_setup import get_logger

logger = get_logger(__name__)


class ExportDataError(RuntimeError):
    """Raised when an export dataset can't be built."""


# Export Center label -> underlying backend.admin_data.DB_TABLES key.
# A subset of the full Database Explorer registry - only the datasets
# named in the Export Center spec, in the order requested.
EXPORT_TABLE_DATASETS: dict[str, str] = {
    "Users": "Users Data",
    "Resume Details": "Resume Details",
    "Resume Reviews": "Resume Reviews",
    "AI Responses": "AI Responses",
    "Feedback": "Feedback",
    "Notifications": "Notifications",
    "Activity Logs": "User Activity Logs",
}

# "Analytics" is handled separately below (get_analytics_export_df), since
# it's a derived summary, not a single Supabase table.
EXPORT_DATASET_LABELS: list[str] = list(EXPORT_TABLE_DATASETS.keys()) + ["Analytics"]


def get_export_dataframe(dataset_label: str) -> pd.DataFrame:
    """Fetch the current, live contents of one Export Center dataset.

    Raises:
        ExportDataError: if the label is unknown or the underlying query fails.
    """
    if dataset_label == "Analytics":
        return get_analytics_export_df()

    db_key = EXPORT_TABLE_DATASETS.get(dataset_label)
    if db_key is None:
        raise ExportDataError(f"Unknown export dataset: '{dataset_label}'")

    try:
        return fetch_table_df(db_key)
    except AdminDataError as exc:
        raise ExportDataError(str(exc)) from exc


def get_export_record_count(dataset_label: str) -> int:
    """Row count for the Export Center's summary list. Returns -1 (not 0)
    on failure, so the UI can distinguish "empty table" from "couldn't load"."""
    try:
        return len(get_export_dataframe(dataset_label))
    except ExportDataError:
        return -1


def get_analytics_export_df() -> pd.DataFrame:
    """Flatten the Analytics snapshot into one exportable table: each row
    is one metric name/value pair, plus the two daily trend series appended
    as their own rows. This is a summary export, not raw event data - the
    raw events are already exportable via the "Activity Logs" dataset.

    Raises:
        ExportDataError: if Supabase can't be reached.
    """
    try:
        snap = get_analytics_snapshot()
    except AnalyticsError as exc:
        raise ExportDataError(str(exc)) from exc

    rows: list[dict[str, str]] = []

    def add(metric: str, value) -> None:
        rows.append({"metric": metric, "value": str(value)})

    add("Daily Active Users", snap.active_users.get("dau", 0))
    add("Weekly Active Users", snap.active_users.get("wau", 0))
    add("Monthly Active Users", snap.active_users.get("mau", 0))
    add("Total Registrations", snap.total_registrations)
    add("Resumes Saved", snap.resume_stats.get("total_saved", 0))
    add("Resume Generation Events", snap.resume_stats.get("generation_events", 0))
    add("Resume Download Events", snap.resume_stats.get("download_events", 0))
    add("Total Resume Reviews", snap.resume_review_stats.get("total_reviews", 0))
    add("Average Resume Score", snap.resume_review_stats.get("average_score"))
    add("Total Roadmaps Generated", snap.ai_roadmap_stats.get("total_roadmaps", 0))
    add("Roadmap Generation Events", snap.ai_roadmap_stats.get("generation_events", 0))
    add("Total AI Chat Exchanges", snap.ai_chatbot_stats.get("total_exchanges", 0))
    add("AI Chatbot Usage Events", snap.ai_chatbot_stats.get("usage_events", 0))
    add("Total Feedback", snap.feedback_stats.get("total", 0))
    add("Average Feedback Rating", snap.feedback_stats.get("average_rating"))
    for status, count in (snap.feedback_stats.get("by_status") or {}).items():
        add(f"Feedback - {status}", count)
    for category, count in (snap.feedback_stats.get("by_category") or {}).items():
        add(f"Feedback - {category}", count)
    add("Notifications Sent", snap.notification_stats.get("total", 0))
    add("Notifications (Broadcast)", snap.notification_stats.get("broadcast", 0))
    add("Notifications (Direct)", snap.notification_stats.get("direct", 0))
    add("Notification Reads", snap.notification_stats.get("total_reads", 0))

    for entry in snap.registration_trend:
        add(f"Registrations on {entry['date']}", entry["count"])
    for entry in snap.login_trend:
        add(f"Logins on {entry['date']}", entry["count"])

    return pd.DataFrame(rows)
