from __future__ import annotations

import streamlit as st

from config.prompts import format_chat_prompt
from config.settings import get_api_key, get_model
from services.knowledge_base import retrieve_context
from services.llm_engine import stream_chat
from utils.state_manager import reserve_ai_request

st.markdown(
    '<section class="hero-panel"><div class="eyebrow">Field-side guidance</div>'
    '<h1>Ask your agronomist.</h1><p>Answers consider your saved farm profile and the latest '
    'weather snapshot when one is available.</p></section>',
    unsafe_allow_html=True,
)
history = st.session_state["messages"]
for message in history:
    avatar = "🧑‍🌾" if message["role"] == "user" else "🌿"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

if "queued_question" in st.session_state:
    st.session_state["chat_input"] = st.session_state.pop("queued_question")

api_key = get_api_key()
question = st.chat_input("Ask about crops, soil, irrigation, or pests…", key="chat_input")
if question:
    history.append({"role": "user", "content": question})
    with st.chat_message("user", avatar="🧑‍🌾"):
        st.markdown(question)
    if not api_key:
        st.warning("Add a Gemini API key in the sidebar to start a live chat.")
    else:
        blocked_reason = reserve_ai_request()
        if blocked_reason:
            st.warning(blocked_reason)
        else:
            weather = st.session_state.get("weather_snapshot")
            current = weather.get("current") if weather else None
            references = retrieve_context(question)
            prompt = format_chat_prompt(
                question,
                st.session_state["farm_profile"],
                current,
                references,
            )
            try:
                with st.chat_message("assistant", avatar="🌿"):
                    answer = st.write_stream(
                        stream_chat(prompt, history[:-1], api_key, get_model())
                    )
                if answer:
                    history.append({"role": "assistant", "content": answer})
                    st.toast("Advice ready", icon="🌱")
                else:
                    st.error("Gemini returned no response. Please try again.")
            except Exception as exc:
                st.error(f"Gemini could not complete the request: {str(exc)[:260]}")

if history and history[-1].get("role") == "assistant":
    st.caption("Quick follow-ups")
    suggestions = ["Show fertilizer options", "Plan an irrigation schedule", "How should I scout for pests?"]
    cols = st.columns(len(suggestions))
    for index, (column, suggestion) in enumerate(zip(cols, suggestions)):
        with column:
            if st.button(suggestion, key=f"chat_suggestion_{index}"):
                st.session_state["queued_question"] = suggestion
                st.rerun()
