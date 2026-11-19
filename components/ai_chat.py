from __future__ import annotations

import streamlit as st

from components.page_header import render_page_header
from config.prompts import format_chat_prompt
from config.settings import get_api_key, get_model
from services.knowledge_base import retrieve_context
from services.llm_engine import gemini_error_message, stream_chat
from utils.state_manager import reserve_ai_request

render_page_header(
    "Ask Novi",
    "Get practical crop, soil, and irrigation advice using your farm profile and available weather.",
    "chat", "✳",
)
history = st.session_state["messages"]
api_key = get_api_key()
if not api_key:
    st.info("Add a Gemini API key under Gemini connection in the sidebar to start a live chat.")

if not history:
    with st.container(border=True, key="chat_starters"):
        st.subheader("What are you working on?")
        with st.container(horizontal=True):
            for index, prompt in enumerate((
                "How often should I water my crop?",
                "What should I check when leaves turn yellow?",
                "How can I improve my soil before planting?",
            )):
                if st.button(prompt, key=f"chat_starter_{index}", disabled=not api_key):
                    st.session_state["queued_question"] = prompt

for message in history:
    avatar = ":material/person:" if message["role"] == "user" else ":material/eco:"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

typed_question = st.chat_input("Ask about crops, soil, irrigation, or pests…", key="chat_input")
question = st.session_state.pop("queued_question", None) or typed_question
if question:
    history.append({"role": "user", "content": question})
    with st.chat_message("user", avatar=":material/person:"):
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
                st.session_state["response_language"],
            )
            try:
                with st.chat_message("assistant", avatar=":material/eco:"):
                    answer = st.write_stream(
                        stream_chat(prompt, history[:-1], api_key, get_model())
                    )
                if answer:
                    history.append({"role": "assistant", "content": answer})
                    st.toast("Advice ready", icon="🌱")
                else:
                    st.error("Gemini returned no response. Please try again.")
            except Exception as exc:
                st.error(gemini_error_message(exc))

if history and history[-1].get("role") == "assistant":
    st.caption("Quick follow-ups")
    suggestions = ["Show fertilizer options", "Plan an irrigation schedule", "How should I scout for pests?"]
    with st.container(horizontal=True, key="chat_followups"):
        for index, suggestion in enumerate(suggestions):
            if st.button(suggestion, key=f"chat_suggestion_{index}"):
                st.session_state["queued_question"] = suggestion
                st.rerun()
