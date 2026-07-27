"""
backend/ai_response_store.py
--------------------------------
Persistence for the AI Mentor chatbot's exchanges, into Supabase's
`ai_responses` table. Direct Supabase access, no Google Sheets / CSV
fallback (same philosophy as backend/resume_details.py in Phase 4).

Design constraint: saving a chat exchange must NEVER break the chat
experience itself. If a user isn't logged in, or Supabase is briefly
unreachable, save_ai_response() logs the problem and returns quietly
rather than raising - the AI generation workflow (backend/openrouter_
client.py, frontend/chatbot.py) is unchanged and unaffected either way.
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
