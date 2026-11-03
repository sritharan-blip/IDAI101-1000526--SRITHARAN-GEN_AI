from __future__ import annotations

import time

import streamlit as st

MAX_AI_REQUESTS_PER_SESSION = 40
AI_REQUEST_COOLDOWN_SECONDS = 2

def initialize_state() -> None:
    defaults = {
        "app_init": True,
        "farm_profile": {"size_ha": 0.0, "soil_type": "Unknown", "ph": 7.0,
                         "latitude": 20.5937, "longitude": 78.9629, "location": "India"},
        "messages": [],
        "chat_history": [],
        "active_theme": "dark",
        "disease_scans": [],
        "weather_snapshot": None,
        "yield_simulation": {},
        "selected_gemini_model": "",
        "model_catalog_key": "",
        "ai_request_count": 0,
        "last_ai_request_at": 0.0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, (dict, list)) else value
    if st.session_state["chat_history"] is not st.session_state["messages"]:
        st.session_state["chat_history"] = st.session_state["messages"]


def reserve_ai_request() -> str | None:
    """Reserve a bounded Gemini request; return a user-facing reason when blocked."""
    if st.session_state["ai_request_count"] >= MAX_AI_REQUESTS_PER_SESSION:
        return "This session reached its AI request limit. Start a new session or try again later."
    now = time.monotonic()
    elapsed = now - st.session_state["last_ai_request_at"]
    if elapsed < AI_REQUEST_COOLDOWN_SECONDS:
        return f"Please wait {AI_REQUEST_COOLDOWN_SECONDS - elapsed:.1f} seconds before the next AI request."
    st.session_state["ai_request_count"] += 1
    st.session_state["last_ai_request_at"] = now
    return None
