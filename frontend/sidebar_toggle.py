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

    function bind() {
        var btn = document.getElementById('lm-sidebar-toggle-btn');
        if (!btn || btn.dataset.lmBound === "1") return;
        btn.dataset.lmBound = "1";
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            var target = findNativeToggle();
            if (target) target.click();
        });
    }

    bind();
    // Retry briefly in case this script runs before the button/native
    // control exist yet (component iframes can mount slightly ahead of
    // the rest of the page on first load).
    setTimeout(bind, 150);
    setTimeout(bind, 500);
})();
</script>
"""


def render_sidebar_toggle() -> None:
    """Render the floating 🎓 sidebar open/close button.

    Call this from inside `with st.sidebar:`, wherever it should appear
    (below the logo, above the nav menu). Purely presentational - it only
    clicks Streamlit's own native sidebar toggle; no app state is read or
    written.
    """
    components.html(_TOGGLE_HTML, height=64, scrolling=False)
