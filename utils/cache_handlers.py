from __future__ import annotations

import streamlit as st

from config.settings import STYLESHEET


@st.cache_resource(show_spinner=False, max_entries=32, ttl=900)
def get_gemini_client(api_key: str):
    from google import genai

    return genai.Client(api_key=api_key, vertexai=False)


def inject_global_styles() -> None:
    theme = st.session_state.get("active_theme", "dark")
    css = STYLESHEET.read_text(encoding="utf-8")
    colors = (
        "color-scheme:dark;--app-bg:#081e19;--app-bg-2:#103327;"
        "--surface:rgba(24,63,48,.82);--surface-strong:#1b4435;"
        "--surface-border:rgba(203,240,209,.23);--text:#f3fff1;--muted:#b8d9c4;"
        "--accent:#ceef94;--accent-strong:#9addb1;--shadow:rgba(0,0,0,.23);"
        "--glow-one:rgba(131,175,64,.32);--glow-two:rgba(78,174,133,.18);"
        "--focus-ring:#9addb1;--primary-ink:#081e19;--switch-off:#426c59;"
        if theme == "dark"
        else "color-scheme:light;--app-bg:#f8fafc;--app-bg-2:#edf5f0;"
        "--surface:#ffffff;--surface-strong:#f1f6f3;"
        "--surface-border:rgba(25,65,48,.16);--text:#172b24;--muted:#52665e;"
        "--accent:#047857;--accent-strong:#047857;--shadow:rgba(20,45,35,.09);"
        "--glow-one:rgba(16,185,129,.10);--glow-two:rgba(14,116,94,.05);"
        "--focus-ring:#047857;--primary-ink:#fff;--switch-off:#647e72;--toolbar-icon-filter:brightness(.18);"
    )
    st.markdown(f"<style>{css}\n:root{{{colors}}}</style>", unsafe_allow_html=True)
