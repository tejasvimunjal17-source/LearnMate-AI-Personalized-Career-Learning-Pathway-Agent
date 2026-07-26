"""
frontend/sidebar_toggle.py
-----------------------------
A custom 🎓 toggle button rendered inside the sidebar (below the logo,
above the nav menu) that opens/closes Streamlit's native sidebar.

Why this needs a small JS snippet: Streamlit doesn't expose a Python API
to collapse/expand the sidebar - that open/closed state lives only in the
browser, not in st.session_state. The only way to toggle it without a
full page rerun is to find Streamlit's own native sidebar-collapse
control in the DOM and simulate a click on it. This button never
reimplements sidebar behavior, touches session state, routing, auth, or
any business logic - it only clicks the exact same native control a user
could otherwise click at the edge of the sidebar.

Rendered via streamlit.components.v1.html (NOT st.markdown) because
<script> tags inserted through st.markdown's unsafe_allow_html are never
executed by the browser (Streamlit injects that HTML via
dangerouslySetInnerHTML, and script tags added that way don't run).
components.v1.html renders in a real iframe, so its <script> does run,
and reaches out to the parent document (same-origin, so this is allowed)
to find and click the real sidebar control.
"""

from __future__ import annotations

import streamlit.components.v1 as components

_TOGGLE_HTML = """
<style>
  html, body { margin: 0; padding: 0; background: transparent; overflow: visible; }
  .lm-sidebar-toggle-wrap {
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 6px 0 10px 0;
  }
  .lm-sidebar-toggle-btn {
      width: 44px;
      height: 44px;
      border-radius: 14px;
      border: 1px solid rgba(255,255,255,0.12);
      background: linear-gradient(120deg, #7C5CFF 0%, #22D3B0 100%);
      color: #fff;
      font-size: 1.25rem;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 6px 18px rgba(124,92,255,0.30);
      transition: transform 280ms ease, box-shadow 280ms ease;
      position: relative;
  }
  .lm-sidebar-toggle-btn:hover {
      transform: translateY(-2px) scale(1.06);
      box-shadow: 0 10px 24px rgba(124,92,255,0.45);
  }
  .lm-sidebar-toggle-btn:active {
      transform: translateY(0) scale(0.94);
  }
  .lm-sidebar-toggle-btn .lm-tooltip {
      position: absolute;
      left: 50%;
      top: 118%;
      transform: translateX(-50%) translateY(-4px);
      background: #1B1E33;
      color: #fff;
      font-family: -apple-system, "Inter", sans-serif;
      font-size: 0.68rem;
      padding: 4px 9px;
      border-radius: 8px;
      white-space: nowrap;
      opacity: 0;
      pointer-events: none;
      transition: opacity 220ms ease, transform 220ms ease;
      z-index: 10001;
  }
  .lm-sidebar-toggle-btn:hover .lm-tooltip {
      opacity: 1;
      transform: translateX(-50%) translateY(0);
  }
  @media (max-width: 640px) {
      .lm-sidebar-toggle-btn { width: 40px; height: 40px; font-size: 1.1rem; }
  }
</style>

<div class="lm-sidebar-toggle-wrap">
  <button class="lm-sidebar-toggle-btn" id="lm-sidebar-toggle-btn" type="button"
          aria-label="Open / Close Navigation">
    🎓
    <span class="lm-tooltip">Open / Close Navigation</span>
  </button>
</div>

<script>
(function () {
    function findNativeToggle() {
        // Streamlit's own sidebar-collapse control - the exact selector
        // differs slightly by Streamlit version and by sidebar state
        // (collapsed vs expanded), so this tries the known variants in
        // order and uses whichever one actually exists right now.
        var doc = window.parent.document;
        return doc.querySelector('[data-testid="stSidebarCollapseButton"] button')
            || doc.querySelector('[data-testid="stSidebarCollapseButton"]')
            || doc.querySelector('[data-testid="collapsedControl"] button')
            || doc.querySelector('[data-testid="collapsedControl"]');
    }

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
