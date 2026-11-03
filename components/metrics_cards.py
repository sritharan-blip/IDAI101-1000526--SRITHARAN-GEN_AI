from __future__ import annotations

from html import escape

import streamlit as st


def render_metric(label: str, value: str, detail: str, icon: str) -> None:
    st.markdown(
        f'<article class="metric-card"><div class="metric-icon">{escape(icon)}</div>'
        f'<div class="metric-label">{escape(label)}</div>'
        f'<div class="metric-value">{escape(value)}</div>'
        f'<div class="metric-detail">{escape(detail)}</div></article>',
        unsafe_allow_html=True,
    )
