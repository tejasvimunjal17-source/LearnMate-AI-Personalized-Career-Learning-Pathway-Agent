"""
backend/supabase_client.py
----------------------------
Replaces backend/sheets_client.py as the storage backend for LearnMate AI.

Design goal: callers (backend/auth.py, backend/resume_store.py,
backend/resume_review.py, backend/responses_store.py) should not need to
change beyond swapping their import line. Those modules were written
against a Google-Sheets-shaped API:

    append_row(sheet_name, header, row_dict)
    read_rows(sheet_name, header) -> list[row_dict]
    update_row(sheet_name, header, match_col, match_value, updates) -> bool

...where `row_dict` uses the *sheet's* column names (e.g. "First Name",
"Email Address"), not the database's snake_case column names, and list
fields are joined into comma/pipe-delimited strings.

Supabase's tables use normalized, snake_case columns and real
arrays/jsonb — and reference users by `user_id` (a foreign key), not by
repeating their email on every row. So this module keeps the exact same
three function names and signatures, but internally:

  1. Maps the sheet_name each caller already passes (e.g. "LearnMate AI
     Users Data") to the real Supabase table name (e.g. "users").
  2. Translates each row dict to/from the DB's column shape for that
     table (_TABLE_ADAPTERS below).
  3. Resolves "email" references to the corresponding users.id.

This keeps 100% of the translation logic in ONE place, so the four
calling modules required only a one-line import change.

Runtime behavior (Phase 4): there is NO local JSON/CSV fallback here
anymore. If SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY aren't configured
or Supabase can't be reached, every function raises SupabaseUnavailableError
immediately. Earlier phases fell back to local JSON storage so the app
could run offline/in demos without credentials configured - that
fallback has been intentionally removed so Supabase is unambiguously
the only runtime data store, with no silent on-disk drift between the
two. Callers that need "never break the user-facing flow over a
persistence hiccup" (e.g. backend/responses_store.py logging a roadmap
request) already wrap their calls in their own try/except - that
resilience now lives at the call site, not hidden inside this module.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any

from config import SHEETS_CONFIG, SUPABASE_CONFIG
from backend.logger_setup import get_logger

logger = get_logger(__name__)

_lock = threading.Lock()
_client_cache: dict[str, Any] = {}


class SupabaseUnavailableError(RuntimeError):
    """Raised internally when Supabase can't be reached; triggers local fallback."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------
def _get_client():
    """Build (and cache) a Supabase client using the service role key.

    The service role key bypasses Row Level Security by design — that is
    intentional and safe here because this module only ever runs on the
    backend (Streamlit server process), never in the browser. Nothing in
    frontend/ imports this module directly or indirectly exposes the key.
    """
    if "client" in _client_cache:
        return _client_cache["client"]

    if not SUPABASE_CONFIG.is_configured:
        raise SupabaseUnavailableError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY are not configured.")

    try:
        from supabase import create_client
    except ImportError as exc:  # pragma: no cover - dependency missing
        raise SupabaseUnavailableError(f"supabase-py not installed: {exc}") from exc

    try:
        client = create_client(SUPABASE_CONFIG.url, SUPABASE_CONFIG.service_role_key)
    except Exception as exc:  # noqa: BLE001
        raise SupabaseUnavailableError(f"Failed to create Supabase client: {exc}") from exc

    _client_cache["client"] = client
    return client


def is_supabase_backend_active() -> bool:
    """Whether reads/writes are currently going to real Supabase (vs. local fallback)."""
    if not SUPABASE_CONFIG.is_configured:
        return False
    try:
        _get_client()
        return True
    except SupabaseUnavailableError:
        return False


# ---------------------------------------------------------------------------
# sheet_name -> table_name mapping
#
# Built from the same config values the calling modules already use, so a
# .env override of e.g. GOOGLE_USERS_SHEET_NAME still resolves correctly
# without editing this file.
# ---------------------------------------------------------------------------
_SHEET_TO_TABLE: dict[str, str] = {
    SHEETS_CONFIG.users_sheet_name: "users",
    "LearnMate AI Users Data": "users",
    SHEETS_CONFIG.responses_sheet_name: "roadmap_requests",
    "LearnMate AI Users Responses": "roadmap_requests",
    SHEETS_CONFIG.resume_review_sheet_name: "resume_reviews",
    "Resume Reviews": "resume_reviews",
    "Users Resume Details": "resume_details",
}


def _table_for(sheet_name: str) -> str:
    table = _SHEET_TO_TABLE.get(sheet_name)
    if not table:
        raise SupabaseUnavailableError(
            f"No Supabase table is mapped for sheet_name='{sheet_name}'. "
            f"Add it to _SHEET_TO_TABLE in backend/supabase_client.py."
        )
    return table


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _split_list(value: Any, sep: str = ", ") -> list[str]:
    if isinstance(value, list):
        return value
    if not value:
        return []
    return [v.strip() for v in str(value).split(sep.strip()) if v.strip()]


def _join_list(value: Any, sep: str = ", ") -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return sep.join(value)


def _fmt_ts(value: Any, fmt: str) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        try:
            # Supabase returns ISO 8601 timestamps (with or without tz offset).
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    else:
        dt = value
    return dt.strftime(fmt)


def _resolve_user_id(client, email: str) -> str | None:
    email_norm = (email or "").strip().lower()
    if not email_norm:
        return None
    resp = client.table("users").select("id").eq("email", email_norm).limit(1).execute()
    rows = resp.data or []
    return rows[0]["id"] if rows else None


# ---------------------------------------------------------------------------
# Per-table adapters: (sheet-shaped row dict) <-> (db-shaped row dict)
#
# Each adapter is a pair of functions:
#   to_db(client, row)     -> dict of real DB columns ready to insert/update
#   from_db(client, row)   -> dict shaped like the old sheet row, for callers
# ---------------------------------------------------------------------------
def _users_to_db(client, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "first_name": row.get("First Name", "").strip(),
        "last_name": row.get("Last Name", "").strip(),
        "email": row.get("Email Address", "").strip().lower(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _users_from_db(client, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "Timestamp": _fmt_ts(row.get("created_at"), "%Y-%m-%d %H:%M:%S UTC"),
        "First Name": row.get("first_name", ""),
        "Last Name": row.get("last_name", ""),
        "Email Address": row.get("email", ""),
    }


def _roadmap_requests_to_db(client, row: dict[str, Any]) -> dict[str, Any]:
    user_id = _resolve_user_id(client, row.get("Email", ""))
    if not user_id:
        raise SupabaseUnavailableError(
            f"Cannot save roadmap request: no users row found for email '{row.get('Email')}'."
        )
    return {
        "user_id": user_id,
        "career_goal": row.get("Career Goal", ""),
        "current_level": row.get("Level", ""),
        "preferred_domain": row.get("Domain", ""),
        "learning_preference": row.get("Learning Preference", ""),
        "study_hours_per_week": int(row.get("Study Hours") or 0),
        "existing_skills": _split_list(row.get("Existing Skills", "")),
    }


def _roadmap_requests_from_db(client, row: dict[str, Any]) -> dict[str, Any]:
    email = (row.get("users") or {}).get("email", "") if isinstance(row.get("users"), dict) else ""
    return {
        "Timestamp": _fmt_ts(row.get("created_at"), "%Y-%m-%d %H:%M:%S UTC"),
        "Email": email,
        "Career Goal": row.get("career_goal", ""),
        "Level": row.get("current_level", ""),
        "Domain": row.get("preferred_domain", ""),
        "Learning Preference": row.get("learning_preference", ""),
        "Study Hours": row.get("study_hours_per_week", ""),
        "Existing Skills": _join_list(row.get("existing_skills", [])),
    }


def _resume_reviews_to_db(client, row: dict[str, Any]) -> dict[str, Any]:
    user_id = _resolve_user_id(client, row.get("email", ""))
    if not user_id:
        raise SupabaseUnavailableError(
            f"Cannot save resume review: no users row found for email '{row.get('email')}'."
        )
    return {
        "user_id": user_id,
        "score": int(row.get("score") or 0),
        "missing_sections": _split_list(row.get("missing_sections", ""), sep=","),
        "strengths": _split_list(row.get("strengths", ""), sep="|"),
        "weaknesses": _split_list(row.get("weaknesses", ""), sep="|"),
        "suggestions": _split_list(row.get("suggestions", ""), sep="|"),
    }


def _resume_reviews_from_db(client, row: dict[str, Any]) -> dict[str, Any]:
    email = (row.get("users") or {}).get("email", "") if isinstance(row.get("users"), dict) else ""
    return {
        "email": email,
        "date": _fmt_ts(row.get("created_at"), "%Y-%m-%d %H:%M UTC"),
        "score": row.get("score", ""),
        "missing_sections": ", ".join(row.get("missing_sections") or []),
        "strengths": " | ".join(row.get("strengths") or []),
        "weaknesses": " | ".join(row.get("weaknesses") or []),
        "suggestions": " | ".join(row.get("suggestions") or []),
    }


def _resume_details_to_db(client, row: dict[str, Any]) -> dict[str, Any]:
    user_id = _resolve_user_id(client, row.get("email", ""))
    if not user_id:
        raise SupabaseUnavailableError(
            f"Cannot save resume details: no users row found for email '{row.get('email')}'."
        )

    def _load_json(value: Any) -> Any:
        if isinstance(value, (list, dict)):
            return value
        try:
            return json.loads(value) if value else []
        except (json.JSONDecodeError, TypeError):
            return []

    return {
        "user_id": user_id,
        "first_name": row.get("first_name", ""),
        "last_name": row.get("last_name", ""),
        "education": row.get("education", ""),
        "skills": _split_list(row.get("skills", "")),
        "certificates": _load_json(row.get("certificates_json")),
        "internships": _load_json(row.get("internships_json")),
        "projects": _load_json(row.get("projects_json")),
        "achievements": row.get("achievements", ""),
        "hobbies": _split_list(row.get("hobbies", "")),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _resume_details_from_db(client, row: dict[str, Any]) -> dict[str, Any]:
    email = (row.get("users") or {}).get("email", "") if isinstance(row.get("users"), dict) else ""
    return {
        "email": email,
        "first_name": row.get("first_name", ""),
        "last_name": row.get("last_name", ""),
        "education": row.get("education", ""),
        "skills": ", ".join(row.get("skills") or []),
        "certificates_json": json.dumps(row.get("certificates") or []),
        "internships_json": json.dumps(row.get("internships") or []),
        "projects_json": json.dumps(row.get("projects") or []),
        "achievements": row.get("achievements", ""),
        "hobbies": ", ".join(row.get("hobbies") or []),
        "created_at": row.get("created_at", ""),
    }


# table_name -> (to_db, from_db, select_clause, match_col_map)
_ADAPTERS: dict[str, dict[str, Any]] = {
    "users": {
        "to_db": _users_to_db,
        "from_db": _users_from_db,
        "select": "*",
        "match_col_map": {"Email Address": "email"},
    },
    "roadmap_requests": {
        "to_db": _roadmap_requests_to_db,
        "from_db": _roadmap_requests_from_db,
        "select": "*, users(email)",
        "match_col_map": {"Email": "users.email"},
    },
    "resume_reviews": {
        "to_db": _resume_reviews_to_db,
        "from_db": _resume_reviews_from_db,
        "select": "*, users(email)",
        "match_col_map": {"email": "users.email"},
    },
    "resume_details": {
        "to_db": _resume_details_to_db,
        "from_db": _resume_details_from_db,
        "select": "*, users(email)",
        "match_col_map": {"email": "users.email"},
    },
}


# ---------------------------------------------------------------------------
# Public API — same names/signatures as backend/sheets_client.py
# ---------------------------------------------------------------------------
def append_row(sheet_name: str, header: list[str], row: dict[str, Any]) -> None:
    """Insert one row (in the caller's original sheet-shaped dict) into Supabase.

    Raises:
        SupabaseUnavailableError: if Supabase isn't configured/reachable,
            or the insert otherwise fails. No local fallback - callers
            that must not let a persistence failure block the user-facing
            flow (e.g. responses_store.save_response) catch this
            themselves at the call site.
    """
    with _lock:
        table = _table_for(sheet_name)
        client = _get_client()
        adapter = _ADAPTERS[table]
        db_row = adapter["to_db"](client, row)
        try:
            client.table(table).insert(db_row).execute()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to insert into Supabase table '%s'", table)
            raise SupabaseUnavailableError(f"Insert into '{table}' failed: {exc}") from exc
        logger.info("Row inserted into Supabase table '%s'", table)


def read_rows(sheet_name: str, header: list[str]) -> list[dict[str, Any]]:
    """Read all rows from Supabase, translated back into the caller's sheet-shaped dicts.

    Raises:
        SupabaseUnavailableError: if Supabase isn't configured/reachable,
            or the read otherwise fails. No local fallback.
    """
    with _lock:
        table = _table_for(sheet_name)
        client = _get_client()
        adapter = _ADAPTERS[table]
        try:
            resp = client.table(table).select(adapter["select"]).execute()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to read Supabase table '%s'", table)
            raise SupabaseUnavailableError(f"Read from '{table}' failed: {exc}") from exc
        return [adapter["from_db"](client, r) for r in (resp.data or [])]


def update_row(sheet_name: str, header: list[str], match_col: str, match_value: str, updates: dict[str, Any]) -> bool:
    """Update the row matching match_col == match_value. Returns True if a row was updated.

    Raises:
        SupabaseUnavailableError: if Supabase isn't configured/reachable,
            or the update otherwise fails. No local fallback.
    """
    with _lock:
        table = _table_for(sheet_name)
        client = _get_client()
        adapter = _ADAPTERS[table]

        # Merge the match value into `updates` so the to_db() adapter has
        # everything it needs (e.g. resume_details updates need "email"
        # present even if the caller didn't repeat it in `updates`).
        merged = {**updates}
        if match_col not in merged:
            merged[match_col] = match_value
        db_row = adapter["to_db"](client, merged)
        # to_db() adapters always resolve/attach user_id; drop it from the
        # SET clause payload only for the `users` table itself, where the
        # match is a plain column (email), not a foreign key.
        db_match_col = adapter["match_col_map"].get(match_col, match_col)

        try:
            if db_match_col.startswith("users."):
                # Matching via the related users table: resolve to user_id first.
                user_id = _resolve_user_id(client, match_value)
                if not user_id:
                    return False
                db_row.pop("user_id", None)
                resp = client.table(table).update(db_row).eq("user_id", user_id).execute()
            else:
                resp = client.table(table).update(db_row).eq(
                    db_match_col, match_value.strip().lower() if db_match_col == "email" else match_value
                ).execute()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to update Supabase table '%s'", table)
            raise SupabaseUnavailableError(f"Update on '{table}' failed: {exc}") from exc

        updated = bool(resp.data)
        if updated:
            logger.info("Row(s) updated in Supabase table '%s'", table)
        return updated
