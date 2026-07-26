"""
frontend/custom_sidebar.py
-----------------------------
A Gmail/Drive-style collapsible sidebar "drawer" for LearnMate AI.

How it works (read before touching this file)
------------------------------------------------
Streamlit provides no public API to resize, hide, or animate its own
sidebar - so any custom collapsible sidebar necessarily has to reach it
via CSS targeting Streamlit's own DOM. This file does exactly that, and
ONLY that: there is no JavaScript anywhere in this file, no click
simulation, no reading/writing Streamlit's internal JS state, and no
iframe. The only Streamlit-internal selectors touched are:

    section[data-testid="stSidebar"]        - the sidebar container itself,
                                               whose WIDTH is animated
                                               (0 <-> full) based on
                                               st.session_state
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapseButton"] - Streamlit's own native
                                               collapse arrow, hidden via
                                               display:none so it doesn't
                                               sit on screen duplicating
                                               our 🎓 button

Everything inside the existing `with st.sidebar:` block in app.py (logo,
nav menu, Dark Mode, Logout, status captions) is completely untouched -
nothing is moved out of st.sidebar. The drawer effect comes purely from
animating that container's width via CSS, which is fundamentally how
Streamlit's own native sidebar-collapse already works visually. Since
Streamlit lays the sidebar and main content out as flex siblings,
shrinking the sidebar's width to 0 makes the main content reflow to fill
the freed space automatically - no separate rule targeting the main
content area is needed.

State
------
st.session_state["sidebar_open"] is the single source of truth (default
True). No JavaScript state, no browser storage - a plain Python boolean,
recomputed into CSS on every rerun.
"""

from __future__ import annotations

import streamlit as st

_SIDEBAR_OPEN_WIDTH = "21rem"
_TRANSITION_MS = 300


def render_custom_sidebar_controls() -> None:
    """Render the 🎓 drawer toggle and apply the resulting open/closed CSS.

    Call this once, early in app.py, OUTSIDE of `with st.sidebar:` - the
    toggle button is fixed-position and independent of the sidebar's own
    box, so it doesn't need to live inside the sidebar to work, and
    staying outside keeps it unaffected by the sidebar's width transition.
    """
    st.session_state.setdefault("sidebar_open", True)

    # ---- Toggle button: rendered in its own container so it can be
    # precisely targeted by CSS and pinned to the viewport corner,
    # completely independent of the sidebar's own animated box. ----
    with st.container(key="lm_drawer_toggle"):
        clicked = st.button(
            "🎓", key="lm_drawer_toggle_btn", help="Open / Close Navigation"
        )
    if clicked:
        st.session_state["sidebar_open"] = not st.session_state["sidebar_open"]

    is_open = st.session_state["sidebar_open"]
    width = _SIDEBAR_OPEN_WIDTH if is_open else "0rem"
    opacity = "1" if is_open else "0"
    pointer_events = "auto" if is_open else "none"
    border_width = "1px" if is_open else "0px"

    st.markdown(
        f"""
        <style>
        /* ---- Fixed toggle button: always visible, always in the same
        spot, regardless of the drawer's open/closed state. ---- */
        div[class*="st-key-lm_drawer_toggle"] {{
            position: fixed;
            top: 14px;
            left: 14px;
            z-index: 1000000;
        }}
        div[class*="st-key-lm_drawer_toggle_btn"] button {{
            width: 44px;
            height: 44px;
            border-radius: 14px;
            padding: 0;
            font-size: 1.2rem;
            box-shadow: 0 6px 18px rgba(124,92,255,0.30);
            transition: transform 280ms ease, box-shadow 280ms ease;
        }}
        div[class*="st-key-lm_drawer_toggle_btn"] button:hover {{
            transform: translateY(-2px) scale(1.05);
            box-shadow: 0 10px 24px rgba(124,92,255,0.45);
        }}

        /* ---- The drawer itself: Streamlit's own sidebar container,
        width-animated between 0 and its normal width. Main content
        reflows automatically since it's a flex sibling of this element -
        no separate rule targeting main content is needed. ---- */
        section[data-testid="stSidebar"] {{
            width: {width} !important;
            min-width: {width} !important;
            max-width: {width} !important;
            border-right-width: {border_width} !important;
            opacity: {opacity};
            pointer-events: {pointer_events};
            overflow: hidden !important;
            transition: width {_TRANSITION_MS}ms ease,
                        min-width {_TRANSITION_MS}ms ease,
                        max-width {_TRANSITION_MS}ms ease,
                        opacity {_TRANSITION_MS - 50}ms ease;
        }}

        /* ---- Hide Streamlit's own native collapse control - fully
        replaced by our 🎓 button above, so it shouldn't also be on
        screen. This is a presentational display:none, not a click or a
        state read - it doesn't affect this drawer's own logic at all. ---- */
        div[data-testid="stSidebarCollapseButton"],
        div[data-testid="collapsedControl"] {{
            display: none !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
