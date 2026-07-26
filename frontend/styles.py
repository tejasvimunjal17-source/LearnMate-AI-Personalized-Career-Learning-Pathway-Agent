"""
frontend/custom_sidebar.py
-----------------------------
A Gmail/Drive-style fixed sliding drawer for LearnMate AI using CSS transforms.
Zero width-based animation, zero ghost slivers, zero layout jumps.
"""

from __future__ import annotations

import streamlit as st

_DRAWER_WIDTH = "21rem"
_TRANSITION_SPEED = "300ms cubic-bezier(0.4, 0.0, 0.2, 1)"


def render_custom_sidebar_controls() -> None:
    """Render the floating 🎓 toggle button, mobile backdrop overlay,
    and CSS transform rules for the custom drawer.
    
    Call this once, early in app.py, OUTSIDE of `with st.sidebar:`.
    """
    st.session_state.setdefault("sidebar_open", True)

    # 1. Floating Toggle Button (Fixed on top-left of screen)
    with st.container(key="lm_drawer_toggle"):
        clicked = st.button(
            "🎓", key="lm_drawer_toggle_btn", help="Toggle Navigation Drawer"
        )
    if clicked:
        st.session_state["sidebar_open"] = not st.session_state["sidebar_open"]

    is_open = st.session_state["sidebar_open"]

    # 2. Backdrop Overlay (Visible on mobile/small viewports when open)
    with st.container(key="lm_drawer_backdrop"):
        backdrop_clicked = st.button(
            "", key="lm_drawer_backdrop_btn", help="Close Navigation"
        )
    if backdrop_clicked:
        st.session_state["sidebar_open"] = False

    # CSS Transform Calculations
    transform_val = "translateX(0)" if is_open else "translateX(-100%)"
    backdrop_display = "block" if is_open else "none"
    desktop_content_margin = _DRAWER_WIDTH if is_open else "0rem"

    st.markdown(
        f"""
        <style>
        /* ---- Hide Native Streamlit Sidebar Controls ---- */
        div[data-testid="stSidebarCollapseButton"],
        div[data-testid="collapsedControl"] {{
            display: none !important;
        }}

        /* ---- Fixed 🎓 Toggle Button ---- */
        div[class*="st-key-lm_drawer_toggle"] {{
            position: fixed !important;
            top: 14px !important;
            left: 14px !important;
            z-index: 1000001 !important;
        }}
        div[class*="st-key-lm_drawer_toggle_btn"] button {{
            width: 44px !important;
            height: 44px !important;
            border-radius: 12px !important;
            padding: 0 !important;
            font-size: 1.25rem !important;
            background-color: var(--background-color, #ffffff) !important;
            border: 1px solid rgba(124, 92, 255, 0.2) !important;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.1) !important;
            transition: transform 200ms ease, box-shadow 200ms ease !important;
            cursor: pointer !important;
        }}
        div[class*="st-key-lm_drawer_toggle_btn"] button:hover {{
            transform: scale(1.05) !important;
            box-shadow: 0 6px 20px rgba(124, 92, 255, 0.25) !important;
        }}

        /* ---- Transform-Based Fixed Drawer ---- */
        section[data-testid="stSidebar"] {{
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            height: 100vh !important;
            width: {_DRAWER_WIDTH} !important;
            min-width: {_DRAWER_WIDTH} !important;
            max-width: {_DRAWER_WIDTH} !important;
            z-index: 1000000 !important;
            transform: {transform_val} !important;
            transition: transform {_TRANSITION_SPEED} !important;
            box-shadow: 4px 0 24px rgba(0, 0, 0, 0.15) !important;
            overflow-y: auto !important;
            visibility: visible !important;
        }}

        /* ---- Main Content Adjustment (Desktop) ---- */
        @media (min-width: 769px) {{
            .stMainBlockContainer,
            div[data-testid="stMain"] {{
                margin-left: {desktop_content_margin} !important;
                transition: margin-left {_TRANSITION_SPEED} !important;
                width: auto !important;
            }}
        }}

        /* ---- Mobile Overlay & Backdrop (Mobile <= 768px) ---- */
        div[class*="st-key-lm_drawer_backdrop"] {{
            display: {backdrop_display} !important;
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100vw !important;
            height: 100vh !important;
            z-index: 999999 !important;
        }}
        div[class*="st-key-lm_drawer_backdrop_btn"] button {{
            width: 100vw !important;
            height: 100vh !important;
            background: rgba(0, 0, 0, 0.4) !important;
            border: none !important;
            border-radius: 0 !important;
            padding: 0 !important;
            cursor: pointer !important;
        }}

        @media (max-width: 768px) {{
            .stMainBlockContainer,
            div[data-testid="stMain"] {{
                margin-left: 0rem !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
