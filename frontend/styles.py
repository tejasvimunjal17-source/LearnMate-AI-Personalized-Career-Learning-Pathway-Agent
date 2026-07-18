"""
frontend/styles.py
---------------------
Design system for the "AI Career Learning Pathway" app.

Concept: the "Pathway" — a glowing constellation trail that represents the
student's journey from where they are to their career goal. Dark, ink-navy
base (mirroring a night sky) with a violet -> teal "aurora" gradient marking
progress, since the whole product's job is to plot and light up a path.

Palette:
    Ink Navy      #0F1229   (dark surface base)
    Paper         #F7F8FC   (light surface base)
    Aurora Violet #7C5CFF   (primary accent - "where you're headed")
    Aurora Teal   #22D3B0   (secondary accent - "progress / growth")
    Slate Text    #2A2F45
    Muted Grey    #8A8FA3

Type:
    Display : "Space Grotesk" - geometric, technical, distinctive headings
    Body    : "Inter" - clean, highly legible body copy
    Mono    : "JetBrains Mono" - stats, numbers, data labels
"""

from __future__ import annotations

import streamlit as st

FONT_IMPORT = (
    "https://fonts.googleapis.com/css2?"
    "family=Space+Grotesk:wght@500;600;700&"
    "family=Inter:wght@400;500;600;700&"
    "family=JetBrains+Mono:wght@500;600&display=swap"
)


def _theme_vars(dark: bool) -> str:
    if dark:
        return """
        --bg: #0F1229;
        --bg-elevated: #161A3A;
        --surface: rgba(255,255,255,0.045);
        --surface-border: rgba(255,255,255,0.09);
        --text: #EDEEFB;
        --text-muted: #9DA3C0;
        --shadow: 0 8px 30px rgba(0,0,0,0.35);
        """
    return """
        --bg: #F7F8FC;
        --bg-elevated: #FFFFFF;
        --surface: rgba(15,18,41,0.035);
        --surface-border: rgba(15,18,41,0.08);
        --text: #1B1E33;
        --text-muted: #5B6079;
        --shadow: 0 8px 24px rgba(30,32,70,0.08);
        """


def inject_css(dark_mode: bool = True) -> None:
    """Inject the full custom design system into the current Streamlit page.

    IMPORTANT: st.markdown() runs its input through a Markdown parser before
    rendering the HTML. Any line indented 4+ spaces is treated as a
    Markdown *code block* and gets escaped/printed as literal text instead
    of being interpreted as HTML - this is what causes raw CSS to "leak"
    onto the page above the UI. To guarantee that never happens, we build
    the CSS with normal (readable) Python indentation below, then strip
    all leading whitespace from every line right before injection. CSS
    itself doesn't care about indentation, so this is purely a rendering
    safeguard.
    """
    theme_vars = _theme_vars(dark_mode)

    # The Google Fonts <link> is injected in its own single-line markdown
    # call, kept separate from the <style> block for the same reason.
    st.markdown(f'<link rel="stylesheet" href="{FONT_IMPORT}">', unsafe_allow_html=True)

    raw_css = f"""
        :root {{
            {theme_vars}
            --violet: #7C5CFF;
            --teal: #22D3B0;
            --gradient: linear-gradient(120deg, #7C5CFF 0%, #22D3B0 100%);
            --radius: 18px;
        }}

        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}

        .stApp {{
            background: var(--bg);
            color: var(--text);
        }}

        #MainMenu, footer, header[data-testid="stHeader"] {{
            background: transparent;
        }}

        /* ---------- Typography ---------- */
        h1, h2, h3, .pathway-display {{
            font-family: 'Space Grotesk', sans-serif !important;
            letter-spacing: -0.01em;
            color: var(--text);
        }}
        p, span, label, div {{
            color: var(--text);
        }}
        .muted {{ color: var(--text-muted) !important; }}
        .mono {{ font-family: 'JetBrains Mono', monospace; }}

        /* ---------- Hero ---------- */
        .hero {{
            padding: 2.2rem 2rem;
            border-radius: var(--radius);
            background: radial-gradient(120% 160% at 0% 0%, rgba(124,92,255,0.18), transparent 60%),
                        radial-gradient(120% 160% at 100% 0%, rgba(34,211,176,0.14), transparent 55%),
                        var(--bg-elevated);
            border: 1px solid var(--surface-border);
            box-shadow: var(--shadow);
            margin-bottom: 1.6rem;
            position: relative;
            overflow: hidden;
        }}
        .hero-eyebrow {{
            display: inline-block;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: var(--teal);
            background: rgba(34,211,176,0.12);
            border: 1px solid rgba(34,211,176,0.3);
            padding: 4px 10px;
            border-radius: 100px;
            margin-bottom: 0.9rem;
        }}
        .hero h1 {{
            font-size: 2.1rem;
            margin: 0 0 0.4rem 0;
            background: var(--gradient);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        /* ---------- Glass Cards ---------- */
        .glass-card {{
            background: var(--bg-elevated);
            border: 1px solid var(--surface-border);
            border-radius: var(--radius);
            padding: 1.4rem 1.5rem;
            box-shadow: var(--shadow);
            margin-bottom: 1.1rem;
            transition: transform 0.18s ease, box-shadow 0.18s ease;
            animation: fadeInUp 0.5s ease both;
        }}
        .glass-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 14px 34px rgba(124,92,255,0.16);
        }}

        .metric-card {{
            background: var(--bg-elevated);
            border: 1px solid var(--surface-border);
            border-radius: 16px;
            padding: 1.1rem 1.2rem;
            box-shadow: var(--shadow);
            animation: fadeInUp 0.5s ease both;
        }}
        .metric-value {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.8rem;
            font-weight: 700;
            background: var(--gradient);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .metric-label {{
            font-size: 0.78rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }}

        /* ---------- Pathway / milestone timeline (signature element) ---------- */
        .pathway-node {{
            position: relative;
            padding: 1rem 1.2rem 1rem 2.6rem;
            margin-bottom: 0.1rem;
            border-left: 2px solid var(--surface-border);
        }}
        .pathway-node::before {{
            content: "";
            position: absolute;
            left: -9px;
            top: 1.3rem;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: var(--gradient);
            box-shadow: 0 0 0 4px var(--bg), 0 0 14px rgba(124,92,255,0.6);
        }}
        .pathway-node:last-child {{ border-left: 2px solid transparent; }}
        .week-chip {{
            display: inline-block;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem;
            color: var(--violet);
            background: rgba(124,92,255,0.12);
            border: 1px solid rgba(124,92,255,0.3);
            padding: 2px 9px;
            border-radius: 100px;
            margin-bottom: 0.4rem;
        }}

        /* ---------- Badges / pills ---------- */
        .pill {{
            display: inline-block;
            font-size: 0.76rem;
            padding: 3px 10px;
            border-radius: 100px;
            margin: 2px 4px 2px 0;
            background: var(--surface);
            border: 1px solid var(--surface-border);
            color: var(--text);
        }}
        .pill-high {{ color: #FF6B81; border-color: rgba(255,107,129,0.4); background: rgba(255,107,129,0.1); }}
        .pill-medium {{ color: #FFC24B; border-color: rgba(255,194,75,0.4); background: rgba(255,194,75,0.1); }}
        .pill-low {{ color: #22D3B0; border-color: rgba(34,211,176,0.4); background: rgba(34,211,176,0.1); }}

        /* ---------- Progress bars ---------- */
        .progress-track {{
            width: 100%;
            height: 10px;
            border-radius: 100px;
            background: var(--surface);
            border: 1px solid var(--surface-border);
            overflow: hidden;
        }}
        .progress-fill {{
            height: 100%;
            border-radius: 100px;
            background: var(--gradient);
            animation: growBar 1s ease-out both;
        }}
        @keyframes growBar {{
            from {{ width: 0%; }}
        }}
        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* ---------- Buttons ---------- */
        .stButton > button, .stDownloadButton > button {{
            background: var(--gradient) !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 0.6rem 1.3rem !important;
            font-weight: 600 !important;
            box-shadow: 0 6px 18px rgba(124,92,255,0.35);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }}
        .stButton > button:hover, .stDownloadButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 24px rgba(124,92,255,0.45);
        }}

        /* ---------- Inputs ---------- */
        .stTextInput input, .stNumberInput input, .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"] > div {{
            background: var(--bg-elevated) !important;
            border-radius: 10px !important;
            border: 1px solid var(--surface-border) !important;
            color: var(--text) !important;
        }}

        /* ---------- Sidebar ---------- */
        section[data-testid="stSidebar"] {{
            background: var(--bg-elevated);
            border-right: 1px solid var(--surface-border);
        }}

        /* ---------- Scrollbar ---------- */
        ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
        ::-webkit-scrollbar-thumb {{ background: var(--surface-border); border-radius: 8px; }}

        /* ---------- Responsive tweaks ---------- */
        @media (max-width: 768px) {{
            .hero {{ padding: 1.4rem 1.2rem; }}
            .hero h1 {{ font-size: 1.5rem; }}
            .glass-card {{ padding: 1.1rem; }}
        }}

        /* Respect reduced motion preference */
        @media (prefers-reduced-motion: reduce) {{
            .glass-card, .metric-card, .progress-fill {{ animation: none !important; }}
        }}

        /* ================= Landing Page ================= */
        .lm-topnav {{
            position: fixed;
            top: 0; left: 0; right: 0;
            z-index: 999;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.9rem 2rem;
            background: color-mix(in srgb, var(--bg-elevated) 88%, transparent);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid var(--surface-border);
        }}
        .lm-topnav-brand {{
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 700;
            font-size: 1.15rem;
        }}
        .lm-topnav-ai {{
            background: var(--gradient);
            -webkit-background-clip: text; background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .lm-topnav-links {{
            font-size: 0.85rem;
            color: var(--text-muted);
        }}
        @media (max-width: 640px) {{
            .lm-topnav-links {{ display: none; }} /* collapses on mobile - hamburger sidebar covers nav */
        }}

        .lm-hero {{
            text-align: center;
            padding: 3.4rem 1.5rem 2.2rem 1.5rem;
            border-radius: var(--radius);
            background: radial-gradient(120% 160% at 50% 0%, rgba(124,92,255,0.22), transparent 60%),
                        radial-gradient(90% 140% at 80% 20%, rgba(34,211,176,0.16), transparent 55%),
                        var(--bg-elevated);
            border: 1px solid var(--surface-border);
            box-shadow: var(--shadow);
            margin-bottom: 1.8rem;
            animation: fadeInUp 0.6s ease both;
        }}
        .lm-hero-badge {{
            display: inline-block;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.74rem;
            letter-spacing: 0.06em;
            color: var(--teal);
            background: rgba(34,211,176,0.12);
            border: 1px solid rgba(34,211,176,0.3);
            padding: 5px 14px;
            border-radius: 100px;
            margin-bottom: 1.2rem;
        }}
        .lm-hero-title {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 2.6rem;
            line-height: 1.15;
            margin: 0 0 1rem 0;
            background: var(--gradient);
            -webkit-background-clip: text; background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .lm-hero-sub {{
            max-width: 620px;
            margin: 0 auto;
            color: var(--text-muted);
            font-size: 1.02rem;
        }}
        .lm-section-title {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.4rem;
            text-align: center;
            margin: 1.6rem 0 1.2rem 0;
        }}
        .lm-feature-card {{ text-align: left; min-height: 150px; }}
        .lm-feature-icon {{ font-size: 1.6rem; margin-bottom: 0.4rem; }}
        .lm-feature-title {{ font-weight: 700; margin-bottom: 4px; }}
        .lm-feature-desc {{ font-size: 0.85rem; line-height: 1.4; }}
        .lm-footer {{
            text-align: center;
            padding: 1.6rem;
            border-top: 1px solid var(--surface-border);
            margin-top: 1rem;
        }}

        @media (max-width: 768px) {{
            .lm-hero-title {{ font-size: 1.8rem; }}
        }}

        /* ================= Floating AI Mentor chatbot ================= */
        div[class*="st-key-lm_chatbot"] {{
            position: fixed !important;
            bottom: 22px;
            right: 22px;
            z-index: 1000;
            width: min(360px, 90vw);
            max-height: 78vh;
            overflow-y: auto;
            background: var(--bg-elevated);
            border: 1px solid var(--surface-border);
            border-radius: 18px;
            box-shadow: 0 16px 40px rgba(0,0,0,0.35);
            padding: 0.9rem 1rem;
        }}
        div[class*="st-key-lm_chatbot"] .stButton > button {{
            width: 100%;
        }}
        @media (max-width: 480px) {{
            div[class*="st-key-lm_chatbot"] {{ right: 10px; bottom: 10px; width: 92vw; }}
        }}

        /* ================= White-label: hide Streamlit chrome ================= */
        /* Hide the top decoration bar and hamburger menu */
        #MainMenu {{ visibility: hidden; }}
        header {{ visibility: hidden; }}
        footer {{ visibility: hidden; }}
        div[data-testid="stHeader"] {{ display: none !important; }}
        div[data-testid="stToolbar"] {{ display: none !important; }}
        div[data-testid="stDecoration"] {{ display: none !important; }}
        div[data-testid="stStatusWidget"] {{ display: none !important; }}

        /* Hide the Fork/GitHub link if applicable */
        #GithubIcon {{ visibility: hidden; }}

        /* Remove top spacing left by hidden headers */
        .block-container {{
            padding-top: 1rem !important;
            padding-bottom: 0rem !important;
        }}
    """

    # Strip all leading whitespace from every line so Streamlit's Markdown
    # parser can never mistake indented CSS for a fenced code block (see
    # the docstring above) — this is the fix for the "raw CSS on screen" bug.
    css = "\n".join(line.lstrip() for line in raw_css.splitlines())
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
