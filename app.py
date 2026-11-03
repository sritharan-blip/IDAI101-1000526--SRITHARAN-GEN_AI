from __future__ import annotations

import streamlit as st

from components.sidebar import render_sidebar
from config.settings import APP_ICON, APP_NAME
from utils.cache_handlers import inject_global_styles
from utils.state_manager import initialize_state

st.set_page_config(page_title=APP_NAME, page_icon=APP_ICON, layout="wide",
                   initial_sidebar_state="expanded")
initialize_state()

pages = [
    st.Page("components/dashboard.py", title="Farm command center", icon=":material/space_dashboard:", default=True),
    st.Page("components/ai_chat.py", title="Agronomist chat", icon=":material/forum:"),
    st.Page("components/vision_scanner.py", title="Crop health scanner", icon=":material/psychiatry:"),
    st.Page("components/yield_simulator.py", title="Yield & finance", icon=":material/monitoring:"),
    st.Page("components/legacy_workflows.py", title="Advisor & insights", icon=":material/agriculture:"),
]
page = st.navigation(pages, position="sidebar", expanded=True)
render_sidebar()
inject_global_styles()
page.run()
