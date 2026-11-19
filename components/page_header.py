from html import escape

import streamlit as st


def render_page_header(title: str, description: str, theme: str, symbol: str) -> None:
    st.html(
        f'<section class="workspace-hero workspace-hero--{escape(theme)}">'
        f'<div class="workspace-intro"><h1>{escape(title)}</h1><p>{escape(description)}</p></div>'
        '<div class="workspace-art" aria-hidden="true">'
        '<span class="workspace-orbit"></span><span class="workspace-orbit workspace-orbit--outer"></span>'
        f'<span class="workspace-symbol">{escape(symbol)}</span></div></section>'
    )
