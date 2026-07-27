"""
backend/notification_store.py
----------------------------------
Data layer for the Notification System (Phase 4, Part 1): admin broadcast
notifications (everyone), direct notifications (one specific user),
read/unread tracking, and notification history — all in Supabase, no
fallback (same Phase 4 convention as the other *_store.py modules).

Distinct from backend/admin_data.py's announcement functions (Phase 3),
which manage the separate, simpler `announcements` table — that feature
is untouched by this module.

Read/unread model: a notification is "read" by a user once a matching
row exists in `notification_reads`. This works the same way for a
broadcast notification (many users, one notification row) and a direct
one (one user) — no per-type branching needed by callers.
"""

from __future__ import annotations

from typing import Any, Optional

from backend.supabase_client import _get_client, SupabaseUnavailableError
from backend.logger_setup import get_logger

logger = get_logger(__name__)

NOTIF_TABLE = "notifications"
READS_TABLE = "notification_reads"


class NotificationStoreError(RuntimeError):
    """Raised when a notification read/write against Supabase fails."""


def _resolve_user_id(client, email: str) -> Optional[str]:
    email_norm = (email or "").strip().lower()
    if not email_norm:
        return None
    resp = client.table("users").select("id").eq("email", email_norm).limit(1).execute()
    rows = resp.data or []
    return rows[0]["id"] if rows else None


# ---------------------------------------------------------------------------
# Admin: sending notifications
# ---------------------------------------------------------------------------
def create_broadcast_notification(title: str, message: str, created_by_admin_id: str) -> None:
    """Send one notification to every user."""
    if not title.strip() or not message.strip():
        raise NotificationStoreError("Title and message are required.")
    try:
        client = _get_client()
        client.table(NOTIF_TABLE).insert(
            {
                "type": "broadcast",
                "user_id": None,
                "title": title.strip(),
                "message": message.strip(),
                "created_by": created_by_admin_id,
                "is_active": True,
            }
        ).execute()
    except SupabaseUnavailableError as exc:
        raise NotificationStoreError(f"Supabase is not configured/reachable: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to create broadcast notification")
        raise NotificationStoreError(f"Could not send broadcast: {exc}") from exc
    logger.info("Broadcast notification sent: '%s'", title)


def create_direct_notification(user_email: str, title: str, message: str, created_by_admin_id: str) -> None:
    """Send one notification to a specific user, by email."""
    if not title.strip() or not message.strip():
        raise NotificationStoreError("Title and message are required.")
    try:
        client = _get_client()
        user_id = _resolve_user_id(client, user_email)
        if not user_id:
            raise NotificationStoreError(f"No registered user found for email '{user_email}'.")
        client.table(NOTIF_TABLE).insert(
            {
                "type": "direct",
                "user_id": user_id,
                "title": title.strip(),
                "message": message.strip(),
                "created_by": created_by_admin_id,
                "is_active": True,
            }
        ).execute()
    except SupabaseUnavailableError as exc:
        raise NotificationStoreError(f"Supabase is not configured/reachable: {exc}") from exc
    except NotificationStoreError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to create direct notification for %s", user_email)
        raise NotificationStoreError(f"Could not send notification: {exc}") from exc
    logger.info("Direct notification sent to %s: '%s'", user_email, title)


def list_all_notifications() -> list[dict[str, Any]]:
    """Admin-side history: every notification ever sent (broadcast + direct)."""
    try:
        client = _get_client()
        resp = (
            client.table(NOTIF_TABLE)
            .select("*, users(email), admin_users(email)")
            .order("created_at", desc=True)
            .execute()
        )
        return resp.data or []
    except SupabaseUnavailableError as exc:
        raise NotificationStoreError(f"Supabase is not configured/reachable: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to list notifications")
        raise NotificationStoreError(f"Could not load notification history: {exc}") from exc


def deactivate_notification(notification_id: str) -> None:
    """Retract a broadcast/direct notification so it stops showing as new."""
    try:
        client = _get_client()
        client.table(NOTIF_TABLE).update({"is_active": False}).eq("id", notification_id).execute()
    except SupabaseUnavailableError as exc:
        raise NotificationStoreError(f"Supabase is not configured/reachable: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to deactivate notification %s", notification_id)
        raise NotificationStoreError(f"Could not retract notification: {exc}") from exc


# ---------------------------------------------------------------------------
# User: notification center
# ---------------------------------------------------------------------------
def get_notifications_for_user(email: str, limit: int = 50) -> list[dict[str, Any]]:
    """Every active notification relevant to this user (broadcast + direct-
    to-them), newest first, each annotated with is_read: bool."""
    try:
        client = _get_client()
        user_id = _resolve_user_id(client, email)
        if not user_id:
            return []

        resp = (
            client.table(NOTIF_TABLE)
            .select("*")
            .eq("is_active", True)
            .or_(f"type.eq.broadcast,user_id.eq.{user_id}")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        notifications = resp.data or []
        if not notifications:
            return []

        reads_resp = (
            client.table(READS_TABLE)
            .select("notification_id")
            .eq("user_id", user_id)
            .execute()
        )
        read_ids = {r["notification_id"] for r in (reads_resp.data or [])}

        for n in notifications:
            n["is_read"] = n["id"] in read_ids
        return notifications
    except SupabaseUnavailableError as exc:
        raise NotificationStoreError(f"Supabase is not configured/reachable: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to load notifications for %s", email)
        raise NotificationStoreError(f"Could not load notifications: {exc}") from exc


def get_unread_count(email: str) -> int:
    """For the notification badge. Returns 0 (not an error) on any failure -
    a badge count must never crash page rendering."""
    try:
        notifications = get_notifications_for_user(email)
        return sum(1 for n in notifications if not n.get("is_read"))
    except NotificationStoreError as exc:
        logger.warning("Could not compute unread count for %s: %s", email, exc)
        return 0


def mark_notification_read(notification_id: str, email: str) -> None:
    try:
        client = _get_client()
        user_id = _resolve_user_id(client, email)
        if not user_id:
            return
        client.table(READS_TABLE).upsert(
            {"notification_id": notification_id, "user_id": user_id},
            on_conflict="notification_id,user_id",
        ).execute()
    except SupabaseUnavailableError as exc:
        raise NotificationStoreError(f"Supabase is not configured/reachable: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to mark notification %s read for %s", notification_id, email)
        raise NotificationStoreError(f"Could not update notification: {exc}") from exc


def mark_all_read(email: str) -> None:
    notifications = get_notifications_for_user(email)
    unread_ids = [n["id"] for n in notifications if not n.get("is_read")]
    for notification_id in unread_ids:
        mark_notification_read(notification_id, email)
