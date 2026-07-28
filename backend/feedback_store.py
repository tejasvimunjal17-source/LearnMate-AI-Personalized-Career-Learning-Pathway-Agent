"""
backend/feedback_store.py
-----------------------------
Persistence for user-submitted feedback (general feedback, bug reports,
feature requests, and platform ratings), into Supabase's `feedback`
table. Direct Supabase access, no Sheets/CSV fallback (same Phase 4
convention as backend/resume_details.py, backend/ai_response_store.py,
backend/roadmap_store.py).

Requires sql/002_feedback_enhancements.sql (rating column, 3-state
status) and sql/006_feedback_category.sql (category column) to have
been run - see FeedbackStoreError messages if they haven't.
"""

from __future__ import annotations

from typing import Optional

from backend.supabase_client import _get_client, SupabaseUnavailableError
from backend.logger_setup import get_logger

logger = get_logger(__name__)

TABLE = "feedback"
VALID_CATEGORIES = ("general", "bug", "feature")


class FeedbackStoreError(RuntimeError):
    """Raised when a feedback submission is invalid or can't be saved."""


def _resolve_user_id(client, email: str) -> Optional[str]:
    email_norm = (email or "").strip().lower()
    if not email_norm:
        return None
    resp = client.table("users").select("id").eq("email", email_norm).limit(1).execute()
    rows = resp.data or []
    return rows[0]["id"] if rows else None


def submit_feedback(
    email: str,
    message: str,
    category: str = "general",
    rating: Optional[int] = None,
) -> None:
    """Submit one feedback item on behalf of a logged-in user.

    Args:
        email: The submitting user's email - required, since feedback.user_id
            is NOT NULL (unlike ai_responses, feedback always belongs to
            someone).
        message: The feedback/bug report/feature request text. Required.
        category: One of "general", "bug", "feature".
        rating: An optional 1-5 platform rating.

    Raises:
        FeedbackStoreError: on invalid input, an unregistered email, or a
            Supabase failure - submissions are important enough that
            silent failure would be worse than surfacing the error to
            the user, unlike the best-effort AI/roadmap logging.
    """
    if not message or not message.strip():
        raise FeedbackStoreError("Feedback message cannot be empty.")
    if category not in VALID_CATEGORIES:
        raise FeedbackStoreError(f"category must be one of {VALID_CATEGORIES}, got '{category}'.")
    if rating is not None and not (1 <= rating <= 5):
        raise FeedbackStoreError("rating must be between 1 and 5.")

    try:
        client = _get_client()
    except SupabaseUnavailableError as exc:
        raise FeedbackStoreError(f"Supabase is not configured/reachable: {exc}") from exc

    user_id = _resolve_user_id(client, email)
    if not user_id:
        raise FeedbackStoreError("You need to be logged in with a registered account to submit feedback.")

    payload = {
        "user_id": user_id,
        "message": message.strip(),
        "category": category,
        "rating": rating,
        "status": "pending",
    }

    try:
        client.table(TABLE).insert(payload).execute()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to save feedback for %s", email)
        raise FeedbackStoreError(f"Could not save your feedback: {exc}") from exc

    logger.info("Feedback submitted by %s (category=%s, rating=%s)", email, category, rating)
