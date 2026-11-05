from __future__ import annotations

import streamlit as st

from config.settings import STYLESHEET


@st.cache_resource(show_spinner=False)
def get_gemini_client(api_key: str):
    from google import genai

    return genai.Client(api_key=api_key)


def inject_global_styles() -> None:
    theme = st.session_state.get("active_theme", "dark")
    css = STYLESHEET.read_text(encoding="utf-8")
    colors = (
        "color-scheme:dark;--app-bg:#071526;--app-bg-2:#0a192f;"
        "--surface:rgba(15,35,54,.72);--surface-strong:rgba(18,45,64,.9);"
        "--surface-border:rgba(190,231,220,.13);--text:#e6f1ff;--muted:#9fb3c8;"
        "--accent:#64ffda;--accent-strong:#10b981;--shadow:rgba(0,0,0,.23);"
        "--glow-one:rgba(16,185,129,.16);--glow-two:rgba(100,255,218,.06);"
        "--focus-ring:rgba(16,185,129,.28);"
        if theme == "dark"
        else "color-scheme:light;--app-bg:#f8fafc;--app-bg-2:#edf5f0;"
        "--surface:#ffffff;--surface-strong:#f1f6f3;"
        "--surface-border:rgba(25,65,48,.16);--text:#172b24;--muted:#52665e;"
        "--accent:#047857;--accent-strong:#047857;--shadow:rgba(20,45,35,.09);"
        "--glow-one:rgba(16,185,129,.10);--glow-two:rgba(14,116,94,.05);"
        "--focus-ring:rgba(4,120,87,.2);"
    )
    st.markdown(f"<style>{css}\n:root{{{colors}}}</style>", unsafe_allow_html=True)
