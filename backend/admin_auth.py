"""
backend/admin_auth.py
------------------------
Authentication for the Admin Panel (built in Phase 3), kept in its own
module and its own `admin_users` table — deliberately separate from
backend/auth.py, which handles the passwordless, email-only login for
regular app users.

Admins get a real password because the Admin Panel exposes destructive
and sensitive operations (user management, database explorer). Passwords
are hashed with bcrypt; the plaintext password is never stored or logged.

This module talks to Supabase directly via backend/supabase_client's
underlying client rather than the generic append_row/read_rows/update_row
sheet-shaped API, since admin_users doesn't have a Google-Sheets-era
shape to stay compatible with — it's a new table with no legacy caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import bcrypt

from backend.supabase_client import _get_client, SupabaseUnavailableError  # noqa: F401 (internal reuse)
from backend.logger_setup import get_logger

logger = get_logger(__name__)


class AdminAuthError(ValueError):
    """Raised for invalid admin credentials or input."""


@dataclass
class AdminUser:
    id: str
    email: str
    first_name: str
    last_name: str
    is_super_admin: bool
    is_active: bool


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
def hash_password(plain_password: str) -> str:
    """Hash a plaintext password with bcrypt. Returns a str safe to store."""
    if not plain_password or len(plain_password) < 8:
        raise AdminAuthError("Password must be at least 8 characters.")
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    if not plain_password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        # Malformed hash (e.g. corrupted row) — never crash the login flow.
        logger.error("Malformed password hash encountered during verification.")
        return False


# ---------------------------------------------------------------------------
# Admin lookup / login
# ---------------------------------------------------------------------------
def get_admin_by_email(email: str) -> dict | None:
    """Return the raw admin_users row for this email, or None."""
    client = _get_client()
    email_norm = (email or "").strip().lower()
    resp = client.table("admin_users").select("*").eq("email", email_norm).limit(1).execute()
    rows = resp.data or []
    return rows[0] if rows else None


def verify_admin_login(email: str, password: str) -> AdminUser:
    """Validate admin credentials. Raises AdminAuthError on any failure.

    Deliberately uses the same error message for "no such admin" and
    "wrong password" so a caller can't enumerate valid admin emails.
    """
    if not email or not password:
        raise AdminAuthError("Email and password are required.")

    try:
        row = get_admin_by_email(email)
    except SupabaseUnavailableError as exc:
        logger.error("Supabase unavailable during admin login: %s", exc)
        raise AdminAuthError(
            "Admin login is temporarily unavailable — the database connection could not be reached."
        ) from exc

    generic_error = "Invalid email or password."
    if row is None:
        raise AdminAuthError(generic_error)
    if not row.get("is_active", True):
        raise AdminAuthError("This admin account has been disabled.")
    if not verify_password(password, row.get("password_hash", "")):
        raise AdminAuthError(generic_error)

    _touch_last_login(row["id"])

    return AdminUser(
        id=row["id"],
        email=row["email"],
        first_name=row.get("first_name", ""),
        last_name=row.get("last_name", ""),
        is_super_admin=bool(row.get("is_super_admin", False)),
        is_active=bool(row.get("is_active", True)),
    )


def _touch_last_login(admin_id: str) -> None:
    try:
        client = _get_client()
        client.table("admin_users").update(
            {"last_login_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", admin_id).execute()
    except Exception:  # noqa: BLE001 - never fail login over a bookkeeping update
        logger.exception("Failed to update last_login_at for admin %s", admin_id)


# ---------------------------------------------------------------------------
# Bootstrapping — creating the first admin account
#
# There is no UI for this yet (Phase 3). Run this once from a local Python
# shell (`python -c "from backend.admin_auth import create_admin_user; ..."`)
# after Phase 2 is deployed, to create your first admin login:
#
#   from backend.admin_auth import create_admin_user
#   create_admin_user("you@example.com", "a-strong-password", "Jane", "Doe", is_super_admin=True)
# ---------------------------------------------------------------------------
def create_admin_user(
    email: str, password: str, first_name: str, last_name: str, is_super_admin: bool = False
) -> AdminUser:
    """Create a new admin_users row. Raises AdminAuthError on invalid input or a duplicate email."""
    email_norm = (email or "").strip().lower()
    if not email_norm or "@" not in email_norm:
        raise AdminAuthError("A valid email is required.")
    if not first_name or not last_name:
        raise AdminAuthError("First and last name are required.")

    password_hash = hash_password(password)  # raises AdminAuthError if too short

    client = _get_client()
    if get_admin_by_email(email_norm) is not None:
        raise AdminAuthError(f"An admin with email '{email_norm}' already exists.")

    resp = (
        client.table("admin_users")
        .insert(
            {
                "email": email_norm,
                "password_hash": password_hash,
                "first_name": first_name.strip(),
                "last_name": last_name.strip(),
                "is_super_admin": is_super_admin,
            }
        )
        .execute()
    )
    row = resp.data[0]
    logger.info("Admin user created: %s", email_norm)
    return AdminUser(
        id=row["id"],
        email=row["email"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        is_super_admin=row["is_super_admin"],
        is_active=row["is_active"],
    )
