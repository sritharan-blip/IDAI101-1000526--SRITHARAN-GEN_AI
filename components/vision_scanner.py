from __future__ import annotations

import hashlib

import streamlit as st

from config.settings import get_api_key, get_model
from services.vision_engine import analyze_crop_image
from utils.state_manager import reserve_ai_request

st.markdown(
    '<section class="hero-panel"><div class="eyebrow">Computer vision · early triage</div>'
    '<h1>Scan a crop symptom.</h1><p>Get a cautious, image-based assessment — not a substitute '
    'for local diagnosis.</p></section>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="dropzone-note">Drop a clear, close-up crop photo below · JPEG, PNG, or WebP · up to 10 MB</div>',
    unsafe_allow_html=True,
)
st.caption("When you analyze a photo, its image bytes are sent to Google Gemini using your configured API key.")
upload = st.file_uploader("Crop photo", type=["jpg", "jpeg", "png", "webp"],
                          label_visibility="collapsed", max_upload_size=10)
if upload:
    image = upload.getvalue()
    if len(image) > 10 * 1024 * 1024:
        st.error("This image is larger than 10 MB. Please upload a smaller crop photo.")
    else:
        st.image(image, caption=upload.name, width=480)
        fingerprint = hashlib.sha256(image).hexdigest()
        completed = next(
            (scan for scan in st.session_state["disease_scans"]
             if scan.get("fingerprint") == fingerprint),
            None,
        )
        if completed is None:
            api_key = get_api_key()
            if not api_key:
                st.info("Add a Gemini API key in the sidebar to analyze this photo.")
            else:
                blocked_reason = reserve_ai_request()
                if blocked_reason:
                    st.warning(blocked_reason)
                else:
                    with st.status("Looking for visible crop symptoms…", expanded=True) as status:
                        try:
                            result = analyze_crop_image(
                                image,
                                upload.type or "image/jpeg",
                                api_key,
                                get_model(),
                            )
                            result["fingerprint"] = fingerprint
                            st.session_state["disease_scans"].append(result)
                            status.update(label="Image assessment ready", state="complete", expanded=False)
                            st.toast("Image assessment complete", icon="🌱")
                            completed = result
                        except Exception as exc:
                            status.update(label="Could not analyze image", state="error", expanded=False)
                            st.error(f"Gemini image analysis failed: {str(exc)[:260]}")

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
else:
    st.caption("Good light and a sharp image of both the affected area and healthy nearby growth can help.")
