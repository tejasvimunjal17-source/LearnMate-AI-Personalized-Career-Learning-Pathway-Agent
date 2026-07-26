"""
frontend/sidebar_toggle.py
-----------------------------
A custom 🎓 button that toggles ONLY the visibility of the in-sidebar
navigation menu (the option_menu list of pages). It does not collapse or
expand Streamlit's native sidebar - the sidebar itself, Dark Mode, the
status captions, and Logout stay visible regardless of this toggle.

State lives in st.session_state["nav_open"] (default True). Pure
Streamlit - no JavaScript, no streamlit.components.v1.html, no DOM
manipulation of any kind.
"""

from __future__ import annotations

import streamlit as st


def render_sidebar_toggle() -> None:
    """Render the 🎓 nav-menu show/hide toggle.

    Call this from inside `with st.sidebar:`, below the logo/title and
    above the nav menu. Sets st.session_state["nav_open"] (default True);
    app.py reads this value to decide whether to render the option_menu.
    """
    st.session_state.setdefault("nav_open", True)

    _, mid_col, _ = st.columns([1, 1, 1])
    with mid_col:
        clicked = st.button(
            "🎓",
            key="lm_nav_toggle_btn",
            help="Open / Close Navigation",
            use_container_width=True,
        )

    if clicked:
        st.session_state["nav_open"] = not st.session_state["nav_open"]
