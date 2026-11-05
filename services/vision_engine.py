from __future__ import annotations

import json

from google.genai import types

from utils.cache_handlers import get_gemini_client

from .llm_engine import get_model_candidates, is_model_unavailable_error


def analyze_crop_image(
    image_bytes: bytes,
    mime_type: str,
    api_key: str,
    model: str,
    response_language: str = "English",
) -> dict:
    prompt = (
        "Inspect this crop image for visible symptoms. Do not claim certainty from an image alone. "
        'Respond only as JSON with exactly these fields: {"disease":"","confidence":0,'
        '"treatment_organic":[],"treatment_chemical":[],"quarantine_required":false}. '
        "Confidence must be an integer from 0 to 100. If uncertain, say 'Uncertain — consult a local "
        "agronomist' and use low confidence. Do not give product brands or exact chemical doses. "
        "Any chemical discussion must advise local confirmation and following the registered product label. "
        f"Write every JSON string value in {response_language}; keep JSON keys in English."
    )
    client = get_gemini_client(api_key)
    last_error: Exception | None = None
    for candidate in get_model_candidates(api_key, model):
        try:
            response = client.models.generate_content(
                model=candidate,
                contents=[
                    prompt,
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                    max_output_tokens=900,
                ),
            )
            result = json.loads(response.text or "")
            if not isinstance(result, dict):
                raise ValueError("Gemini returned an unexpected scan result.")
            confidence = max(0, min(100, int(result.get("confidence", 0))))
            return {
                "disease": str(result.get("disease") or "Uncertain — consult a local agronomist"),
                "confidence": confidence,
                "treatment_organic": _clean_list(result.get("treatment_organic")),
                "treatment_chemical": _clean_list(result.get("treatment_chemical")),
                "quarantine_required": bool(result.get("quarantine_required", False)),
                "model": candidate,
            }
        except Exception as exc:
            last_error = exc
            if isinstance(exc, ValueError):
                raise RuntimeError(f"Could not parse Gemini's crop scan response: {exc}") from exc
            if not is_model_unavailable_error(exc):
                raise
    raise RuntimeError(f"No available Gemini vision model completed the scan: {last_error}")


def _clean_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
