"""
frontend/custom_sidebar.py
-----------------------------
A Gmail/Drive-style collapsible sidebar "drawer" mechanism for LearnMate AI.
Used by BOTH the regular user app (via render_custom_sidebar_controls, the
original public function - unchanged name/signature/behavior) and the
Admin Panel (via render_admin_sidebar_controls, added so the Admin Panel
gets the identical professional collapse/expand experience without
duplicating ~150 lines of CSS).

How it works (read before touching this file)
------------------------------------------------
Streamlit provides no public API to resize, hide, or animate its own
sidebar - so a custom collapsible sidebar necessarily has to reach it via
CSS targeting Streamlit's own DOM. This file does exactly that, and ONLY
that: no JavaScript, no click simulation, no reading/writing Streamlit's
internal JS state, no iframe.

Why `position: fixed` + `transform`, not a width animation
-------------------------------------------------------------
An earlier version of this file animated the sidebar's `width` between
0 and its normal value. That produced a partially-visible "sliver" bug:
Streamlit's actual sidebar/main layout isn't guaranteed to be sized
purely by that one CSS property (it may involve an inner content wrapper
with its own intrinsic width, or a CSS Grid track sized independently of
the section's own `width`) - so shrinking `width` alone didn't fully
match what the layout engine reserved space for.

`position: fixed` sidesteps that entirely: once an element is taken out
of the normal document flow, no grid/flexbox sizing algorithm affects it
anymore - it becomes an independent floating layer, and `transform:
translateX()` slides that whole layer (identical width at all times, so
nothing inside it "shrinks" or "clips") fully on/off screen.

Because the sidebar is no longer part of the flex/grid flow, main
content no longer reflows into its space automatically - so this file
also sets an explicit `margin-left` + `width: calc(100% - drawer width)`
on the main content container on desktop, toggled in sync with the same
transition (the width/max-width constraint is what prevents the
main-content overflow/shift bug that a margin-left alone would cause -
see the comment inside _render_drawer_css). On mobile, the drawer instead
overlays on top of the content (no margin shift), with a tap-to-close
backdrop - matching how the Gmail/Drive Android drawer behaves.

The only Streamlit-internal selectors touched are:

    section[data-testid="stSidebar"]         - the sidebar, repositioned
                                                fixed + slid via transform
    section[data-testid="stMain"], .main     - main content, margin-left
                                                + width animated on desktop
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapseButton"]  - Streamlit's own native
                                                collapse arrow, hidden
                                                (display:none) since our
                                                toggle button replaces it

Whatever is rendered inside `with st.sidebar:` (in either app.py for the
regular user, or frontend/admin_panel.py for the Admin Panel) is
completely untouched by this file - nothing is moved out of st.sidebar.

Independence between the user sidebar and the Admin Panel sidebar
----------------------------------------------------------------------
The two callers use entirely separate state keys and entirely separate
Streamlit widget key prefixes (see USER_SIDEBAR / ADMIN_SIDEBAR below),
so opening/closing one has zero effect on the other's state - they only
share the underlying CSS-generation *code*, not any session state. Since
app.py's ADMIN_MODE gate always st.stop()s before the regular user flow
would render (and vice versa), the two toggle buttons/backdrops are also
never mounted on the same page at the same time, so there is no risk of
duplicate-key or visual-overlap issues between them despite reusing the
same fixed screen position.
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

_DRAWER_WIDTH = "21rem"
_DRAWER_WIDTH_MOBILE = "min(21rem, 85vw)"
_TRANSITION_MS = 300


@dataclass(frozen=True)
class _SidebarSpec:
    state_key: str        # st.session_state key holding open/closed (bool)
    key_prefix: str        # Streamlit widget key prefix (must be unique per sidebar)
    icon: str                # toggle button glyph


USER_SIDEBAR = _SidebarSpec(state_key="sidebar_open", key_prefix="lm_drawer", icon="🎓")
ADMIN_SIDEBAR = _SidebarSpec(state_key="admin_sidebar_open", key_prefix="lm_admin_drawer", icon="🛡️")


def _render_drawer(spec: _SidebarSpec) -> None:
    """Render one drawer's toggle button, mobile backdrop, and CSS. Shared
    implementation behind both public functions below - see _SidebarSpec
    for what actually varies between the user and admin drawers."""
    st.session_state.setdefault(spec.state_key, True)
    is_open = st.session_state[spec.state_key]

    toggle_container_key = f"{spec.key_prefix}_toggle"
    toggle_btn_key = f"{spec.key_prefix}_toggle_btn"
    backdrop_container_key = f"{spec.key_prefix}_backdrop"
    backdrop_btn_key = f"{spec.key_prefix}_backdrop_btn"

    # ---- Toggle button: always visible, always in the same spot. ----
    with st.container(key=toggle_container_key):
        toggle_clicked = st.button(spec.icon, key=toggle_btn_key, help="Open / Close Navigation")

    # ---- Mobile tap-to-close backdrop: a real (always-rendered) button,
    # shown only via a CSS media query on small screens and only while the
    # drawer is open. Clicking it closes the drawer, same as tapping
    # outside a Gmail/Drive Android drawer. ----
    with st.container(key=backdrop_container_key):
        backdrop_clicked = st.button("", key=backdrop_btn_key, help="Close navigation")

    if toggle_clicked or (backdrop_clicked and is_open):
        st.session_state[spec.state_key] = not st.session_state[spec.state_key]
        is_open = st.session_state[spec.state_key]

    transform = "translateX(0)" if is_open else "translateX(-100%)"
    backdrop_display = "block" if is_open else "none"
    main_margin = _DRAWER_WIDTH if is_open else "0"

    st.markdown(
        f"""
        <style>
        /* ---- Fixed toggle button: always visible, always in the same
        spot, regardless of the drawer's open/closed state. ---- */
        div[class*="st-key-{toggle_container_key}"] {{
            position: fixed;
            top: 14px;
            left: 14px;
            z-index: 1000000;
        }}
        div[class*="st-key-{toggle_btn_key}"] button {{
            width: 44px;
            height: 44px;
            border-radius: 14px;
            padding: 0;
            font-size: 1.2rem;
            box-shadow: 0 6px 18px rgba(124,92,255,0.30);
            transition: transform 280ms ease, box-shadow 280ms ease;
        }}
        div[class*="st-key-{toggle_btn_key}"] button:hover {{
            transform: translateY(-2px) scale(1.05);
            box-shadow: 0 10px 24px rgba(124,92,255,0.45);
        }}

        /* ---- The drawer itself: taken out of document flow so no
        grid/flex sizing algorithm can partially-clip it - always full
        width, purely slid on/off screen via transform. ---- */
        section[data-testid="stSidebar"] {{
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            height: 100vh !important;
            width: {_DRAWER_WIDTH} !important;
            min-width: {_DRAWER_WIDTH} !important;
            max-width: {_DRAWER_WIDTH} !important;
            z-index: 999998;
            overflow-y: auto !important;
            transform: {transform};
            transition: transform {_TRANSITION_MS}ms ease;
        }}
        @media (max-width: 640px) {{
            section[data-testid="stSidebar"] {{
                width: {_DRAWER_WIDTH_MOBILE} !important;
                min-width: {_DRAWER_WIDTH_MOBILE} !important;
                max-width: {_DRAWER_WIDTH_MOBILE} !important;
            }}
        }}

        /* ---- Desktop only: main content margin shifts in sync with the
        drawer, since it's no longer a flex/grid sibling that reflows on
        its own. On mobile the drawer overlays instead (no margin shift -
        see the backdrop below).

        Why width/max-width are set here too, not just margin-left: once
        the sidebar is taken out of flow (position: fixed, above), the
        flex container that normally splits space between sidebar + main
        no longer reserves any room for it - stMain ends up sized as if
        it owns the full viewport width on its own. Adding margin-left
        on top of that already-100%-wide box pushes the total occupied
        width to 100% + drawer width, overflowing past the right edge of
        the screen. Explicitly constraining width/max-width to
        `calc(100% - drawer width)` guarantees the box always fits
        exactly beside the drawer, however Streamlit's internal
        flex/grid sizing happens to compute it. ---- */
        @media (min-width: 641px) {{
            section[data-testid="stMain"], .main {{
                margin-left: {main_margin} !important;
                width: calc(100% - {main_margin}) !important;
                max-width: calc(100% - {main_margin}) !important;
                transition: margin-left {_TRANSITION_MS}ms ease, width {_TRANSITION_MS}ms ease;
            }}
        }}

        /* ---- Defensive guard against a momentary horizontal scrollbar
        during the translateX() transition on some browsers. Never clips
        real content - nothing in the layout is wider than the viewport
        once the rule above is applied. ---- */
        html, body, .stApp {{
            overflow-x: hidden !important;
        }}

        /* ---- Mobile tap-to-close backdrop: invisible/inert on desktop,
        a dim full-screen tap target on mobile while the drawer is open. ---- */
        div[class*="st-key-{backdrop_container_key}"] {{
            display: none;
        }}
        @media (max-width: 640px) {{
            div[class*="st-key-{backdrop_container_key}"] {{
                display: {backdrop_display};
                position: fixed;
                inset: 0;
                z-index: 999997;
            }}
            div[class*="st-key-{backdrop_btn_key}"] button {{
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.45) !important;
                border: none !important;
                box-shadow: none !important;
                cursor: pointer;
            }}
        }}

        /* ---- Hide Streamlit's own native collapse control - fully
        replaced by our toggle button above. Presentational display:none
        only, not a click or a state read. ---- */
        div[data-testid="stSidebarCollapseButton"],
        div[data-testid="collapsedControl"] {{
            display: none !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_custom_sidebar_controls() -> None:
    """Render the 🎓 drawer toggle, the mobile tap-to-close backdrop, and
    apply the resulting open/closed CSS, for the regular (non-admin) app.

    Call this once, early in app.py, OUTSIDE of `with st.sidebar:` - both
    the toggle button and the backdrop are independent, fixed-position
    elements, so they don't need to live inside the sidebar to work.

    Unchanged from before this file was refactored to support the Admin
    Panel too - same name, same signature, same behavior, same
    st.session_state["sidebar_open"] key.
    """
    _render_drawer(USER_SIDEBAR)


def render_admin_sidebar_controls() -> None:
    """The Admin Panel's equivalent of render_custom_sidebar_controls():
    same collapsible-drawer mechanism, same visual treatment, but with the
    🛡️ icon and its own independent st.session_state["admin_sidebar_open"]
    key and widget key prefix - opening/closing this one has no effect on
    the regular user sidebar's state, and vice versa.

    Call this once, early in frontend/admin_panel.py's render_admin_panel(),
    OUTSIDE of `with st.sidebar:` - same placement rule as the user version.
    """
    _render_drawer(ADMIN_SIDEBAR)
