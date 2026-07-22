"""
config.py
---------
Centralized, secure configuration loader for the AI Career Learning Pathway app.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)


def _get_env(key: str, default: str | None = None, required: bool = False) -> str:
    """Fetch an environment variable, optionally trying Streamlit secrets too."""
    value = os.getenv(key, default)

    if not value:
        try:
            import streamlit as st

            if hasattr(st, "secrets"):
                if key in st.secrets:
                    val = st.secrets[key]
                    if isinstance(val, dict):
                        value = json.dumps(val)
                    else:
                        value = str(val)
                # Auto-fallback for gcp_service_account block in secrets.toml
                elif key == "GOOGLE_SERVICE_ACCOUNT_JSON" and "gcp_service_account" in st.secrets:
                    value = json.dumps(dict(st.secrets["gcp_service_account"]))
        except Exception:
            pass

    if required and not value:
        raise EnvironmentError(f"Missing required environment variable '{key}'.")
    return value or ""


@dataclass(frozen=True)
class WatsonxConfig:
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
    service_account_file: str
    service_account_json: str
    users_sheet_name: str
    responses_sheet_name: str

    @property
    def is_configured(self) -> bool:
        return bool(self.service_account_file or self.service_account_json)


@dataclass(frozen=True)
class OrchestrateConfig:
    orchestration_id: str
    host_url: str
    deployment_platform: str
    crn: str
    agent_id: str
    agent_environment_id: str

    @property
    def is_configured(self) -> bool:
        return bool(
            self.orchestration_id
            and self.host_url
            and self.agent_id
            and self.agent_environment_id
        )


@dataclass(frozen=True)
class OpenRouterConfig:
    api_key: str
    model: str

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.model)


def load_config() -> WatsonxConfig:
    return WatsonxConfig(
        api_key=_get_env("WATSONX_API_KEY", required=False),
        project_id=_get_env("WATSONX_PROJECT_ID", required=False),
        base_url=_get_env("WATSONX_URL", default="https://us-south.ml.cloud.ibm.com"),
        model_id=_get_env("WATSONX_MODEL_ID", default="ibm/granite-3-8b-instruct"),
        api_version=_get_env("WATSONX_API_VERSION", default="2024-05-01"),
        app_env=_get_env("APP_ENV", default="development"),
    )


def load_sheets_config() -> GoogleSheetsConfig:
    return GoogleSheetsConfig(
        service_account_file=_get_env("GOOGLE_SERVICE_ACCOUNT_FILE", required=False),
        service_account_json=_get_env("GOOGLE_SERVICE_ACCOUNT_JSON", required=False),
        users_sheet_name=_get_env("GOOGLE_USERS_SHEET_NAME", default="LearnMate AI Users Data"),
        responses_sheet_name=_get_env(
            "GOOGLE_RESPONSES_SHEET_NAME", default="LearnMate AI Users Responses"
        ),
    )


def load_orchestrate_config() -> OrchestrateConfig:
    return OrchestrateConfig(
        orchestration_id=_get_env("WATSONX_ORCHESTRATION_ID"),
        host_url=_get_env("WATSONX_HOST_URL"),
        deployment_platform=_get_env(
            "WATSONX_DEPLOYMENT_PLATFORM",
            default="ibmcloud",
        ),
        crn=_get_env("WATSONX_CRN"),
        agent_id=_get_env("WATSONX_AGENT_ID"),
        agent_environment_id=_get_env("WATSONX_AGENT_ENVIRONMENT_ID"),
    )


def load_openrouter_config() -> OpenRouterConfig:
    return OpenRouterConfig(
        api_key=_get_env("OPENROUTER_API_KEY", required=False),
        model=_get_env("OPENROUTER_MODEL", default="openai/gpt-4o-mini"),
    )


CONFIG = load_config()
SHEETS_CONFIG = load_sheets_config()
ORCHESTRATE_CONFIG = load_orchestrate_config()
OPENROUTER_CONFIG = load_openrouter_config()
