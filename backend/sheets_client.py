"""
backend/sheets_client.py
-------------------------
Thin, defensive data-access layer that stores LearnMate AI's two datasets —
user registrations and roadmap-form responses — in Google Sheets.

Why a fallback matters: this project must run out of the box on Streamlit
Community Cloud's free tier *before* anyone has wired up a Google Cloud
service account. So exactly like backend/watsonx_client.py falls back to an
offline roadmap generator, this module falls back to local CSV storage under
./data/ whenever Google credentials aren't configured or the Sheets API call
fails. The public functions (append_row / read_rows) behave identically
either way, so callers (backend/auth.py) never need to know which backend is
active.

Google Sheets auth uses a service-account key (gspread + google-auth).
Grant that service account "Editor" access to the target spreadsheet.
"""

from __future__ import annotations

import csv
import json
import threading
from pathlib import Path
from typing import Any

from config import SHEETS_CONFIG
from backend.logger_setup import get_logger

logger = get_logger(__name__)

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_lock = threading.Lock()

_client_cache: dict[str, Any] = {}


class SheetsUnavailableError(RuntimeError):
    """Raised internally when the Google Sheets API can't be reached."""


def _local_path(sheet_name: str) -> Path:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    safe = sheet_name.strip().lower().replace(" ", "_")
    return _DATA_DIR / f"{safe}.csv"


def _get_gspread_client():
    """Build (and cache) an authorized gspread client, or raise if unavailable."""
    if "client" in _client_cache:
        return _client_cache["client"]

    if not SHEETS_CONFIG.is_configured:
        raise SheetsUnavailableError("Google Sheets credentials are not configured.")

    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError as exc:  # pragma: no cover - dependency missing
        raise SheetsUnavailableError(f"gspread/google-auth not installed: {exc}") from exc

    try:
        if SHEETS_CONFIG.service_account_json:
            info = json.loads(SHEETS_CONFIG.service_account_json)
            creds = Credentials.from_service_account_info(info, scopes=_SCOPES)
        else:
            creds = Credentials.from_service_account_file(
                SHEETS_CONFIG.service_account_file, scopes=_SCOPES
            )
        client = gspread.authorize(creds)
    except Exception as exc:  # noqa: BLE001
        raise SheetsUnavailableError(f"Failed to authorize Google Sheets client: {exc}") from exc

    _client_cache["client"] = client
    return client


def _get_or_create_worksheet(sheet_name: str, header: list[str]):
    client = _get_gspread_client()
    try:
        # Check if sheet_name is a full Google Sheets URL
        if sheet_name.startswith("http"):
            spreadsheet = client.open_by_url(sheet_name)
        else:
            spreadsheet = client.open(sheet_name)
    except Exception as exc:
        logger.error("Could not open sheet '%s': %s", sheet_name, exc)
        raise SheetsUnavailableError(f"Spreadsheet '{sheet_name}' not accessible: {exc}") from exc
        
    worksheet = spreadsheet.sheet1
    existing_header = worksheet.row_values(1)
    if existing_header != header:
        worksheet.update("A1", [header])
    return worksheet


def is_sheets_backend_active() -> bool:
    """Whether reads/writes are currently going to real Google Sheets (vs. local fallback)."""
    if not SHEETS_CONFIG.is_configured:
        return False
    try:
        _get_gspread_client()
        return True
    except SheetsUnavailableError:
        return False


def append_row(sheet_name: str, header: list[str], row: dict[str, Any]) -> None:
    """Append one row (keyed by `header`) to the given sheet, Sheets-first with local fallback."""
    ordered_values = [str(row.get(col, "")) for col in header]

    with _lock:
        try:
            worksheet = _get_or_create_worksheet(sheet_name, header)
            worksheet.append_row(ordered_values, value_input_option="USER_ENTERED")
            logger.info("Row appended to Google Sheet '%s'", sheet_name)
            return
        except SheetsUnavailableError as exc:
            logger.info("Google Sheets unavailable (%s) — using local fallback storage.", exc)
        except Exception:  # noqa: BLE001
            logger.exception("Unexpected error writing to Google Sheets — using local fallback.")

        path = _local_path(sheet_name)
        file_exists = path.exists()
        with path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=header)
            if not file_exists:
                writer.writeheader()
            writer.writerow({col: row.get(col, "") for col in header})


def read_rows(sheet_name: str, header: list[str]) -> list[dict[str, Any]]:
    """Read all rows from the given sheet as a list of dicts, Sheets-first with local fallback."""
    with _lock:
        try:
            worksheet = _get_or_create_worksheet(sheet_name, header)
            records = worksheet.get_all_records()
            return list(records)
        except SheetsUnavailableError as exc:
            logger.info("Google Sheets unavailable (%s) — reading local fallback storage.", exc)
        except Exception:  # noqa: BLE001
            logger.exception("Unexpected error reading Google Sheets — using local fallback.")

        path = _local_path(sheet_name)
        if not path.exists():
            return []
        with path.open("r", newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))


def update_row(sheet_name: str, header: list[str], match_col: str, match_value: str, updates: dict[str, Any]) -> bool:
    """Update the first row where `match_col` == `match_value`. Returns True if a row was updated."""
    with _lock:
        try:
            worksheet = _get_or_create_worksheet(sheet_name, header)
            cell = worksheet.find(match_value)
            if cell is None:
                return False
            row_values = worksheet.row_values(cell.row)
            row_dict = dict(zip(header, row_values + [""] * (len(header) - len(row_values))))
            row_dict.update(updates)
            worksheet.update(f"A{cell.row}", [[str(row_dict.get(col, "")) for col in header]])
            return True
        except SheetsUnavailableError as exc:
            logger.info("Google Sheets unavailable (%s) — updating local fallback storage.", exc)
        except Exception:  # noqa: BLE001
            logger.exception("Unexpected error updating Google Sheets — using local fallback.")

        path = _local_path(sheet_name)
        if not path.exists():
            return False
        rows = list(csv.DictReader(path.open("r", newline="", encoding="utf-8")))
        updated = False
        for r in rows:
            if r.get(match_col) == match_value:
                r.update({k: str(v) for k, v in updates.items()})
                updated = True
        if updated:
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=header)
                writer.writeheader()
                writer.writerows(rows)
        return updated
