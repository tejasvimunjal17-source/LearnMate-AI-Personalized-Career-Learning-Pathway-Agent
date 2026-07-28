"""
backend/ai_response_store.py
--------------------------------
Persistence for the AI Mentor chatbot's exchanges, into Supabase's
`ai_responses` table. Direct Supabase access, no Google Sheets / CSV
fallback (same philosophy as backend/resume_details.py and
backend/roadmap_store.py).

Design constraint: saving a chat exchange must NEVER break the chat
experience itself. If a user isn't logged in, or Supabase is briefly
unreachable, save_ai_response() logs the problem and returns quietly
rather than raising - the AI generation workflow (backend/openrouter_
client.py, frontend/chatbot.py) is unchanged and unaffected either way.

delete_ai_response_for_user(), by contrast, is a user-initiated action
(from frontend/profile_page.py's AI History tab) and follows the same
raise-on-failure convention as backend/resume_details.py and
backend/roadmap_store.py's delete functions - a delete the user asked
for should surface a real error if it didn't work, not fail silently.
"""

from __future__ import annotations

from typing import Any, Optional

from backend.supabase_client import _get_client, SupabaseUnavailableError
from backend.logger_setup import get_logger

logger = get_logger(__name__)

TABLE = "ai_responses"


def _resolve_user_id(client, email: Optional[str]) -> Optional[str]:
    """Best-effort email -> users.id lookup. Returns None (not an error) if
    the caller wasn't logged in or no matching user exists - ai_responses.
    user_id is nullable specifically to allow this."""
    email_norm = (email or "").strip().lower()
    if not email_norm:
        return None
    try:
        resp = client.table("users").select("id").eq("email", email_norm).limit(1).execute()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to resolve user_id for AI response logging (email=%s)", email_norm)
        return None
    rows = resp.data or []
    return rows[0]["id"] if rows else None


def save_ai_response(
    email: Optional[str],
    prompt: str,
    response: str,
    model: str = "",
    tokens_used: Optional[int] = None,
    response_time_ms: Optional[int] = None,
) -> None:
    """Log one AI Mentor chatbot exchange. Best-effort: never raises.

    Args:
        email: The logged-in user's email, or None if not logged in
            (the chatbot widget is visible pre-login too). Resolved to
            users.id internally; stored as NULL if not resolvable.
        prompt: The user's message.
        response: The AI Mentor's reply.
        model: The model identifier used to generate the reply (e.g. from
            config.OPENROUTER_CONFIG.model). Stored as '' if unknown.
        tokens_used: Total tokens for this exchange, if the caller has it
            available. Stored as NULL (not fabricated) if not available -
            generate_chat_response()'s current return contract is a plain
            string with no usage data attached.
        response_time_ms: Wall-clock time for the AI call, in milliseconds,
            if the caller measured it. Stored as NULL if not provided.
    """
    if not prompt or not prompt.strip() or not response or not response.strip():
        return  # nothing meaningful to log

    try:
        client = _get_client()
    except SupabaseUnavailableError as exc:
        logger.warning("Supabase unavailable - AI response not logged: %s", exc)
        return

    user_id = _resolve_user_id(client, email)

    payload: dict[str, Any] = {
        "user_id": user_id,
        "prompt": prompt.strip(),
        "response": response.strip(),
        "model": model or "",
        "tokens_used": tokens_used,
        "response_time_ms": response_time_ms,
    }

    try:
        client.table(TABLE).insert(payload).execute()
    except Exception:  # noqa: BLE001 - logging must never break the chat UX
        logger.exception("Failed to save AI response to Supabase (user_id=%s)", user_id)
        return

    logger.info("AI response logged (user_id=%s, model=%s)", user_id, model)


def delete_ai_response_for_user(response_id: str, user_id: str) -> None:
    """Delete one ai_responses row, scoped to both id AND user_id so a user
    can only ever delete their own AI chat history - never another user's,
    even if a response_id from someone else's history were somehow passed
    in.

    Raises:
        SupabaseUnavailableError: if Supabase isn't configured/reachable.
        RuntimeError: if the delete otherwise fails.
    """
    try:
        client = _get_client()
    except SupabaseUnavailableError as exc:
        logger.error(
            "Supabase unavailable - could not delete ai_responses id=%s for user_id=%s: %s",
            response_id, user_id, exc,
        )
        raise

    try:
        resp = client.table(TABLE).delete().eq("id", response_id).eq("user_id", user_id).execute()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to delete ai_responses id=%s for user_id=%s", response_id, user_id)
        raise RuntimeError(f"Could not delete AI chat entry: {exc}") from exc

    if resp.data:
        logger.info("AI response deleted (id=%s, user_id=%s)", response_id, user_id)
    else:
        logger.warning(
            "Delete request for ai_responses id=%s matched no row for user_id=%s (already deleted, or not owned by this user)",
            response_id, user_id,
        )
