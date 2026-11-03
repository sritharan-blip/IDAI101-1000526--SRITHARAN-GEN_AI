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
DEFAULT_MODEL = "gemini-2.5-flash"
MODEL_FALLBACKS = (DEFAULT_MODEL, "gemini-2.5-flash-lite")
TRUSTED_SOURCES = {
    "FAO": "https://www.fao.org/",
    "India agriculture": "https://agriwelfare.gov.in/",
    "ICAR": "https://icar.org.in/",
    "Ghana MoFA": "https://mofa.gov.gh/",
    "Agriculture and Agri-Food Canada": "https://agriculture.canada.ca/",
}


def get_api_key() -> str:
    """Resolve credentials from Streamlit Secrets, environment, then user input."""
    try:
        secret = st.secrets.get("GEMINI_API_KEY", "")
    except (FileNotFoundError, KeyError, StreamlitSecretNotFoundError):
        secret = ""
    return (
        str(secret).strip()
        or os.environ.get("GEMINI_API_KEY", "").strip()
        or st.session_state.get("gemini_api_key_input", "").strip()
    )


def has_secret_api_key() -> bool:
    try:
        return bool(str(st.secrets.get("GEMINI_API_KEY", "")).strip())
    except (FileNotFoundError, KeyError, StreamlitSecretNotFoundError):
        return False


def get_model() -> str:
    custom_model = st.session_state.get("custom_model_id", "").strip()
    return custom_model or st.session_state.get("selected_gemini_model", DEFAULT_MODEL)
