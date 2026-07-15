"""
config.py
---------
Centralized, secure configuration loader for the AI Career Learning Pathway app.

All secrets (API keys, project IDs, endpoints) are loaded exclusively from
environment variables (via a local .env file in development, or platform
"Secrets" in production e.g. Streamlit Community Cloud / IBM Code Engine).

NOTHING sensitive is hard-coded here. If a required variable is missing,
the app fails fast with a clear, actionable error instead of running with
broken credentials.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load variables from a local .env file if present (development convenience).
# In production (e.g. Streamlit Cloud) secrets are injected as real
# environment variables / st.secrets, so this call is a harmless no-op.
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)


def _get_env(key: str, default: str | None = None, required: bool = False) -> str:
    """Fetch an environment variable, optionally trying Streamlit secrets too."""
    value = os.getenv(key, default)

    # Fallback to st.secrets when running on Streamlit Cloud, if available.
    if not value:
        try:
            import streamlit as st  # local import to avoid hard dependency at import time

            if hasattr(st, "secrets") and key in st.secrets:
                value = st.secrets[key]
        except Exception:
            pass

    if required and not value:
        raise EnvironmentError(
            f"Missing required environment variable '{key}'. "
            f"Copy .env.example to .env and set it, or configure it in "
            f"Streamlit secrets."
        )
    return value or ""


@dataclass(frozen=True)
class WatsonxConfig:
    """Immutable, validated configuration for the IBM watsonx.ai connection."""

    api_key: str
    project_id: str
    base_url: str
    model_id: str
    api_version: str
    app_env: str

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.project_id and self.base_url and self.model_id)


@dataclass(frozen=True)
class GoogleSheetsConfig:
    """Configuration for the Google Sheets backend (user registrations + roadmap responses).

    Accepts credentials either as a path to a service-account JSON key file
    (GOOGLE_SERVICE_ACCOUNT_FILE) or as the raw JSON content itself
    (GOOGLE_SERVICE_ACCOUNT_JSON) - the latter is convenient for Streamlit
    Community Cloud secrets, which don't support uploading files.
    """

    service_account_file: str
    service_account_json: str
    users_sheet_name: str
    responses_sheet_name: str

    @property
    def is_configured(self) -> bool:
        return bool(self.service_account_file or self.service_account_json)


@dataclass(frozen=True)
class OrchestrateConfig:
    """Configuration for the IBM watsonx Orchestrate AI Mentor chat widget."""

    embed_url: str
    agent_id: str

    @property
    def is_configured(self) -> bool:
        return bool(self.embed_url)


def load_config() -> WatsonxConfig:
    """Load and return the application's watsonx.ai configuration."""
    return WatsonxConfig(
        api_key=_get_env("WATSONX_API_KEY", required=False),
        project_id=_get_env("WATSONX_PROJECT_ID", required=False),
        base_url=_get_env("WATSONX_URL", default="https://us-south.ml.cloud.ibm.com"),
        model_id=_get_env("WATSONX_MODEL_ID", default="ibm/granite-3-8b-instruct"),
        api_version=_get_env("WATSONX_API_VERSION", default="2024-05-01"),
        app_env=_get_env("APP_ENV", default="development"),
    )


def load_sheets_config() -> GoogleSheetsConfig:
    """Load and return the Google Sheets backend configuration."""
    return GoogleSheetsConfig(
        service_account_file=_get_env("GOOGLE_SERVICE_ACCOUNT_FILE", required=False),
        service_account_json=_get_env("GOOGLE_SERVICE_ACCOUNT_JSON", required=False),
        users_sheet_name=_get_env("GOOGLE_USERS_SHEET_NAME", default="LearnMate AI Users Data"),
        responses_sheet_name=_get_env(
            "GOOGLE_RESPONSES_SHEET_NAME", default="LearnMate AI Users Responses"
        ),
    )


def load_orchestrate_config() -> OrchestrateConfig:
    """Load and return the IBM watsonx Orchestrate chat-widget configuration."""
    return OrchestrateConfig(
        embed_url=_get_env("WATSONX_ORCHESTRATE_EMBED_URL", required=False),
        agent_id=_get_env("WATSONX_ORCHESTRATE_AGENT_ID", required=False),
    )


# Singleton-style config instances used across the app
CONFIG = load_config()
SHEETS_CONFIG = load_sheets_config()
ORCHESTRATE_CONFIG = load_orchestrate_config()
