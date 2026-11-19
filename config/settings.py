from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

APP_NAME = "AgroNova | Farm intelligence"
APP_ICON = "🌱"
DATA_DIR = Path(os.environ.get("GENAI_DATA_DIR", "data"))
ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"
STYLESHEET = Path(__file__).resolve().parents[1] / "styles" / "global.css"
DEFAULT_MODEL = "gemini-3.5-flash-lite"
MODEL_FALLBACKS = (
    DEFAULT_MODEL,
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.1-flash-lite",
)
MODEL_DESCRIPTIONS = {
    "gemini-3.8-flash": "Newest Flash · high capability and speed",
    "gemini-3.6-flash": "Stable Flash · balanced general-purpose option",
    "gemini-3.5-flash-lite": "Flash-Lite · fast and cost-efficient",
    "gemini-3.1-flash-lite": "Flash-Lite · stable, low-cost alternative",
}
TRUSTED_SOURCES = {
    "FAO": "https://www.fao.org/",
    "India agriculture": "https://agriwelfare.gov.in/",
    "ICAR": "https://icar.org.in/",
    "Ghana MoFA": "https://mofa.gov.gh/",
    "Agriculture and Agri-Food Canada": "https://agriculture.canada.ca/",
}


def _usable_key(value: object) -> str:
    key = value.strip() if isinstance(value, str) else ""
    if key.lower().startswith(("paste-", "your-key", "your-gemini-")):
        return ""
    return key


def configured_api_key() -> str:
    """Resolve a server-side credential from Streamlit Secrets or the environment."""
    try:
        secret = st.secrets.get("GEMINI_API_KEY", "")
    except (FileNotFoundError, KeyError, StreamlitSecretNotFoundError):
        secret = ""
    return _usable_key(secret) or _usable_key(os.environ.get("GEMINI_API_KEY"))


def get_api_key() -> str:
    return configured_api_key() or _usable_key(st.session_state.get("gemini_api_key_input"))


def get_model() -> str:
    custom_model = st.session_state.get("custom_model_id", "").strip()
    return custom_model or st.session_state.get("selected_gemini_model") or DEFAULT_MODEL
