"""
backend/auth.py
------------------
User registration, lookup, and profile-update logic for LearnMate AI.

Registrations are persisted via backend.supabase_client into the
Supabase "users" table, with columns: Timestamp, First Name, Last Name,
Email Address (translated internally to created_at/first_name/last_name/
email). As of Phase 4 there is no local fallback: if Supabase can't be
reached, the functions below raise RegistrationError with a clear
message rather than silently degrading to on-disk storage.

This module deliberately holds no session logic of its own — Streamlit
session state (st.session_state["auth_user"]) is the source of truth for
"who is logged in right now"; this module is only responsible for
persistence and validation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from config import SHEETS_CONFIG
from backend.supabase_client import append_row, read_rows, update_row, SupabaseUnavailableError
from backend.logger_setup import get_logger

logger = get_logger(__name__)

USERS_HEADER = ["Timestamp", "First Name", "Last Name", "Email Address"]

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z\s.'-]{0,49}$")


@dataclass
class AuthUser:
    first_name: str
    last_name: str
    email: str
    registration_date: str

    def to_dict(self) -> dict:
        return asdict(self)


class RegistrationError(ValueError):
    """Raised when registration input fails validation."""


def validate_registration(first_name: str, last_name: str, email: str) -> list[str]:
    errors: list[str] = []
    if not first_name or not first_name.strip():
        errors.append("First name is required.")
    elif not NAME_RE.match(first_name.strip()):
        errors.append("First name should contain only letters (2-50 chars).")

    if not last_name or not last_name.strip():
        errors.append("Last name is required.")
    elif not NAME_RE.match(last_name.strip()):
        errors.append("Last name should contain only letters (2-50 chars).")

    if not email or not email.strip():
        errors.append("Email address is required.")
    elif not EMAIL_RE.match(email.strip()):
        errors.append("Please enter a valid email address.")

    return errors


def find_user_by_email(email: str) -> AuthUser | None:
    """Look up a previously-registered user by email. Returns None if not found.

    Raises RegistrationError if Supabase can't be reached (there is no
    local fallback to quietly fall back to as of Phase 4).
    """
    email_norm = email.strip().lower()
    try:
        rows = read_rows(SHEETS_CONFIG.users_sheet_name, USERS_HEADER)
    except SupabaseUnavailableError as exc:
        logger.error("Could not look up user %s: %s", email_norm, exc)
        raise RegistrationError(
            "We couldn't reach the database right now. Please try again in a moment."
        ) from exc
    for row in rows:
        if str(row.get("Email Address", "")).strip().lower() == email_norm:
            return AuthUser(
                first_name=row.get("First Name", ""),
                last_name=row.get("Last Name", ""),
                email=row.get("Email Address", ""),
                registration_date=row.get("Timestamp", ""),
            )
    return None


def register_user(first_name: str, last_name: str, email: str) -> AuthUser:
    """Validate, check for duplicates, and persist a new user registration.

    Raises RegistrationError on invalid input or a duplicate email.
    Returns the newly-created AuthUser (which also acts as the login record
    for returning users, since this app uses passwordless email-based
    sessions per the product spec).
    """
    errors = validate_registration(first_name, last_name, email)
    if errors:
        raise RegistrationError(" ".join(errors))

    existing = find_user_by_email(email)
    if existing is not None:
        raise RegistrationError(
            "An account with this email already exists. "
            "Use 'Continue with existing email' to log back in instead."
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    row = {
        "Timestamp": timestamp,
        "First Name": first_name.strip(),
        "Last Name": last_name.strip(),
        "Email Address": email.strip().lower(),
    }
    try:
        append_row(SHEETS_CONFIG.users_sheet_name, USERS_HEADER, row)
    except SupabaseUnavailableError as exc:
        logger.error("Could not register user %s: %s", row["Email Address"], exc)
        raise RegistrationError(
            "We couldn't reach the database right now. Please try again in a moment."
        ) from exc
    logger.info("New user registered: %s", row["Email Address"])

    return AuthUser(
        first_name=row["First Name"],
        last_name=row["Last Name"],
        email=row["Email Address"],
        registration_date=timestamp,
    )


def login_existing_user(email: str) -> AuthUser:
    """Look up a user for a passwordless 'continue with email' login."""
    if not email or not EMAIL_RE.match(email.strip()):
        raise RegistrationError("Please enter a valid email address.")
    user = find_user_by_email(email)
    if user is None:
        raise RegistrationError("No account found with that email. Please register first.")
    return user


def update_user_name(email: str, first_name: str, last_name: str) -> bool:
    """Update a registered user's first/last name. Returns True on success."""
    errors = []
    if not first_name or not NAME_RE.match(first_name.strip()):
        errors.append("First name should contain only letters (2-50 chars).")
    if not last_name or not NAME_RE.match(last_name.strip()):
        errors.append("Last name should contain only letters (2-50 chars).")
    if errors:
        raise RegistrationError(" ".join(errors))

    try:
        updated = update_row(
            SHEETS_CONFIG.users_sheet_name,
            USERS_HEADER,
            match_col="Email Address",
            match_value=email.strip().lower(),
            updates={"First Name": first_name.strip(), "Last Name": last_name.strip()},
        )
    except SupabaseUnavailableError as exc:
        logger.error("Could not update profile for %s: %s", email, exc)
        raise RegistrationError(
            "We couldn't reach the database right now. Please try again in a moment."
        ) from exc
    if updated:
        logger.info("Profile updated for %s", email)
    return updated
