from __future__ import annotations

import hashlib

import streamlit as st

from config.languages import RESPONSE_LANGUAGES, format_language_option
from config.settings import MODEL_DESCRIPTIONS, MODEL_FALLBACKS, get_api_key, has_secret_api_key
from services.llm_engine import list_models
from utils.pdf_generator import generate_farm_report


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("# 🌱 AgroNova")
        st.caption("Field intelligence · powered by Gemini")
        dark = st.toggle(
            "Dark glass theme",
            value=st.session_state.get("active_theme") == "dark",
            key="theme_toggle",
        )
        st.session_state["active_theme"] = "dark" if dark else "light"
        st.divider()

        st.selectbox(
            "AI response language",
            RESPONSE_LANGUAGES,
            format_func=format_language_option,
            key="response_language",
        )

        st.markdown("#### Your farm")
        profile = st.session_state["farm_profile"]
        st.session_state.setdefault("profile_location", profile["location"])
        location = st.text_input("Farm location", key="profile_location")
        latitude, longitude = st.columns(2)
        lat = latitude.number_input("Latitude", min_value=-90.0, max_value=90.0,
                                    value=float(st.session_state["farm_profile"]["latitude"]),
                                    step=0.01, format="%.4f", key="profile_latitude")
        lon = longitude.number_input("Longitude", min_value=-180.0, max_value=180.0,
                                     value=float(st.session_state["farm_profile"]["longitude"]),
                                     step=0.01, format="%.4f", key="profile_longitude")
        size = st.number_input("Farm size (hectares)", min_value=0.0, max_value=100000.0,
                               value=float(st.session_state["farm_profile"]["size_ha"]),
                               step=0.5, key="profile_size")
        soil = st.selectbox("Soil type", ["Unknown", "Sandy", "Loamy", "Clay", "Silty", "Other"],
                            index=["Unknown", "Sandy", "Loamy", "Clay", "Silty", "Other"].index(
                                st.session_state["farm_profile"]["soil_type"]),
                            key="profile_soil")
        ph = st.slider("Soil pH (if known)", 3.0, 10.0,
                       float(st.session_state["farm_profile"]["ph"]), 0.1, key="profile_ph")
        st.session_state["farm_profile"] = {
            "location": location or "Not specified",
            "latitude": lat,
            "longitude": lon,
            "size_ha": size,
            "soil_type": soil,
            "ph": ph,
        }

        st.divider()
        st.markdown("#### Gemini connection")
        api_key = get_api_key()
        if not has_secret_api_key():
            st.text_input(
                "Gemini API key",
                type="password",
                key="gemini_api_key_input",
                placeholder="Paste key or use GEMINI_API_KEY",
                help="Saved for this browser session only. For deployment, use Streamlit Secrets.",
            )
            api_key = get_api_key()

        model_options = list(MODEL_FALLBACKS)
        if api_key:
            try:
                available = list_models(api_key)
                if available:
                    model_options = available
                else:
                    st.warning("No text-generation models were returned for this key.")
            except Exception:
                st.warning("Could not load Gemini models. You can still enter a model name below.")
        catalog_key = hashlib.sha256(api_key.encode()).hexdigest() if api_key else ""
        if st.session_state.get("model_catalog_key") != catalog_key:
            st.session_state["selected_gemini_model"] = model_options[0]
            st.session_state["model_catalog_key"] = catalog_key
        elif st.session_state.get("selected_gemini_model") not in model_options:
            st.session_state["selected_gemini_model"] = model_options[0]
        st.selectbox(
            "Gemini model",
            model_options,
            key="selected_gemini_model",
            help="The newest model is selected by default. Choose a faster or lower-cost option if preferred.",
        )
        description = MODEL_DESCRIPTIONS.get(st.session_state["selected_gemini_model"])
        if description:
            st.caption(description)
        st.text_input(
            "Custom model ID (optional)",
            key="custom_model_id",
            placeholder="gemini-…",
            help="Use this when Google enables a model before it appears in the list.",
        )
        st.download_button(
            "Download farm action plan",
            data=generate_farm_report(st.session_state),
            file_name="farm-action-plan.pdf",
            mime="application/pdf",
            width="stretch",
            icon=":material/download:",
        )
        st.caption(
            "AI prompts include your farm profile; chat and uploaded photos are sent to Google Gemini. "
            "Weather comes from Open-Meteo; satellite vegetation data is not connected."
        )
