from __future__ import annotations

import re
from collections.abc import Iterator

import streamlit as st
from google.genai.errors import APIError

from config.settings import DEFAULT_MODEL, MODEL_FALLBACKS
from utils.cache_handlers import get_gemini_client


@st.cache_data(ttl=900, show_spinner=False, max_entries=32)
def list_models(api_key: str) -> list[str]:
    client = get_gemini_client(api_key)
    models = client.models.list(config={"page_size": 100})
    names = []
    for model in models:
        name = (getattr(model, "name", "") or "").rsplit("/", 1)[-1]
        actions = getattr(model, "supported_actions", None) or []
        if (name.startswith("gemini-") and "generateContent" in actions
                and not any(part in name for part in ("-image", "-tts", "-live", "-robotics", "-computer-use"))):
            names.append(name)
    return sorted(set(names), key=_model_sort_key)


def _model_sort_key(name: str) -> tuple:
    if name.endswith("-latest"):
        return (0, (), name)
    match = re.match(r"^gemini-(\d+(?:\.\d+)?)-(.+)$", name)
    if not match:
        return (1, (), name)
    version = tuple(-int(part) for part in match.group(1).split("."))
    family = match.group(2)
    family_rank = 0 if family.startswith("flash") and "lite" not in family else 1
    return (1, version, family_rank, name)


def get_model_candidates(api_key: str, preferred: str) -> list[str]:
    try:
        available = list_models(api_key)
    except Exception:
        available = []
    candidates = [preferred, *MODEL_FALLBACKS, *available]
    if available:
        candidates = [name for name in candidates if name == preferred or name in available]
    return list(dict.fromkeys(candidates))


def is_model_unavailable_error(error: Exception) -> bool:
    if not isinstance(error, APIError):
        return False
    message = str(error).lower()
    return error.code == 404 or (
        error.code == 400 and "model" in message
        and any(term in message for term in ("not supported", "deprecated", "no longer"))
    )


def gemini_error_message(error: Exception | None) -> str:
    """Describe common Gemini failures without displaying raw provider data."""
    if isinstance(error, APIError):
        details = str(error).lower()
        if error.code in (401, 403) or "api_key_invalid" in details or "api key not valid" in details:
            return "Gemini rejected the API key or its permissions. Check Gemini connection or the deployment secret."
        if error.code == 429:
            return "Gemini is over its rate or quota limit. Check the project quota or try again later."
        if is_model_unavailable_error(error):
            return "Gemini could not use the selected model. Choose another model under Gemini connection."
        if isinstance(error.code, int) and error.code >= 500:
            return "Gemini is temporarily unavailable. Try again in a moment."
    return "Gemini could not complete the request. Check the connection and try again."


def generate_text(prompt: str, api_key: str, model: str, temperature: float = 0.35,
                  max_tokens: int = 1200) -> str:
    client = get_gemini_client(api_key)
    last_error: Exception | None = None
    for candidate in get_model_candidates(api_key, model):
        try:
            response = client.models.generate_content(
                model=candidate,
                contents=prompt,
                config={"temperature": temperature, "max_output_tokens": max_tokens},
            )
            text = (response.text or "").strip()
            if text:
                return text
            raise RuntimeError("Gemini returned an empty response.")
        except Exception as exc:
            last_error = exc
            if not is_model_unavailable_error(exc):
                raise
    raise last_error


def stream_chat(prompt: str, history: list[dict], api_key: str, model: str) -> Iterator[str]:
    client = get_gemini_client(api_key)
    conversation = []
    for item in history[-10:]:
        role = "Farmer" if item.get("role") == "user" else "Agronomist"
        conversation.append(f"{role}: {item.get('content', '')}")
    contents = prompt
    if conversation:
        contents = "Recent conversation:\n" + "\n".join(conversation) + "\n\nCurrent request:\n" + prompt

    last_error: Exception | None = None
    for candidate in get_model_candidates(api_key, model):
        started = False
        try:
            stream = client.models.generate_content_stream(
                model=candidate,
                contents=contents,
                config={"temperature": 0.4, "max_output_tokens": 4096},
            )
            for chunk in stream:
                if chunk.text:
                    started = True
                    yield chunk.text
            return
        except Exception as exc:
            last_error = exc
            if started or not is_model_unavailable_error(exc):
                raise
    raise last_error
