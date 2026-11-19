from __future__ import annotations

import hashlib
from io import BytesIO

import streamlit as st
from PIL import Image

from components.page_header import render_page_header
from config.settings import get_api_key, get_model
from services.llm_engine import gemini_error_message
from services.vision_engine import analyze_crop_image
from utils.state_manager import reserve_ai_request

render_page_header(
    "Crop health scanner",
    "Check visible symptoms and get possible causes and lower-risk next steps.",
    "scan", "⌖",
)
upload_col, guide_col = st.columns([1.6, 1], gap="medium")
with upload_col, st.container(border=True, key="scan_upload"):
    st.subheader("Upload a crop photo")
    upload = st.file_uploader("Crop photo", type=["jpg", "jpeg", "png", "webp"],
                              label_visibility="collapsed", max_upload_size=10)
    st.caption("Your photo is sent to Gemini when you select Analyze photo.")
with guide_col, st.container(border=True, key="scan_guide"):
    st.subheader("Get a clearer scan")
    st.markdown("1. Photograph the affected area in daylight.\n"
                "2. Keep the symptoms sharp and close.\n"
                "3. Include healthy growth for comparison if possible.")
if upload:
    image = upload.getvalue()
    response_language = st.session_state["response_language"]
    if len(image) > 10 * 1024 * 1024:
        st.error("This image is larger than 10 MB. Please upload a smaller crop photo.")
    else:
        try:
            with Image.open(BytesIO(image)) as photo:
                mime_type = Image.MIME.get(photo.format)
                photo.load()
        except (OSError, Image.DecompressionBombError):
            mime_type = None
        if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
            st.error("This file could not be opened as a JPEG, PNG, or WebP photo.")
            st.stop()
        with st.container(border=True, key="scan_preview"):
            st.image(image, caption=upload.name, width=480)
        fingerprint = hashlib.sha256(response_language.encode("utf-8") + b"\0" + image).hexdigest()
        completed = next(
            (scan for scan in st.session_state["disease_scans"]
             if scan.get("fingerprint") == fingerprint),
            None,
        )
        if completed is None:
            api_key = get_api_key()
            if not api_key:
                st.info("Add a Gemini API key in the sidebar to analyze this photo.")
            elif st.button("Analyze photo", type="primary"):
                blocked_reason = reserve_ai_request()
                if blocked_reason:
                    st.warning(blocked_reason)
                else:
                    with st.status("Looking for visible crop symptoms…", expanded=True) as status:
                        try:
                            result = analyze_crop_image(
                                image,
                                mime_type,
                                api_key,
                                get_model(),
                                response_language,
                            )
                            result["fingerprint"] = fingerprint
                            st.session_state["disease_scans"].append(result)
                            status.update(label="Image assessment ready", state="complete", expanded=False)
                            st.toast("Image assessment complete", icon="🌱")
                            completed = result
                        except Exception as exc:
                            status.update(label="Could not analyze image", state="error", expanded=False)
                            st.error(gemini_error_message(exc))

        if completed:
            confidence = completed["confidence"]
            st.subheader(completed["disease"])
            confidence_color = "#34d399" if confidence >= 75 else "#fbbf24" if confidence >= 40 else "#f87171"
            st.markdown(
                f'<div class="confidence-track" role="progressbar" aria-label="Model confidence" '
                f'aria-valuemin="0" aria-valuemax="100" aria-valuenow="{confidence}">'
                f'<div class="confidence-fill" '
                f'style="width:{confidence}%;background:{confidence_color}"></div></div>',
                unsafe_allow_html=True,
            )
            st.caption(f"Model confidence: {confidence}% · image-based estimate")
            st.warning(
                "A photo cannot confirm a diagnosis. Check leaf undersides and nearby plants, "
                "and contact your local extension service before treatment."
            )
            if completed["quarantine_required"]:
                st.warning("The model suggests isolation may be needed. Seek local plant-health advice promptly.")
            with st.expander("Lower-risk and cultural steps", expanded=True):
                if completed["treatment_organic"]:
                    for step in completed["treatment_organic"]:
                        st.markdown(f"- {step}")
                else:
                    st.caption("No specific lower-risk action was returned.")
            with st.expander("Chemical treatment notes"):
                if completed["treatment_chemical"]:
                    for step in completed["treatment_chemical"]:
                        st.markdown(f"- {step}")
                    st.caption("Use only products registered for this crop and location; follow the full label.")
                else:
                    st.caption("No chemical treatment was suggested.")
            st.caption(f"Gemini model: {completed['model']} · This is preliminary AI triage, not a diagnosis.")
