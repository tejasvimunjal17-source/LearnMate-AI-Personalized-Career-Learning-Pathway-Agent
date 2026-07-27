"""
backend/resume_templates.py
------------------------------
Template registry for the Resume Builder's "Resume Template" gallery.

Each entry is pure metadata + style tokens - no rendering logic lives
here and this module has no dependency on resume_store.py or
resume_generator.py, so it can be added without touching either file.
backend/resume_generator.py (once template-aware) reads a template's
`style` dict to decide fonts, colors, and layout for both the PDF and
DOCX renderers, and frontend/resume_builder.py reads `name`/
`description`/`ats_score`/etc. to draw the gallery cards and the HTML
live preview.

Keeping this as a separate, data-only module means adding a new
template later is a matter of adding one TemplateSpec here - no changes
needed to any renderer's control flow.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TemplateStyle:
    """Fonts/layout tokens consumed by the PDF and DOCX renderers."""
    heading_font: str = "Helvetica-Bold"      # reportlab base-14 font
    body_font: str = "Helvetica"
    docx_font: str = "Calibri"                # python-docx font family name
    header_style: str = "plain"               # "plain" | "banner" | "sidebar-bar" | "centered-rule"
    name_align: str = "left"                  # "left" | "center"
    divider: bool = True                      # thin rule under section headings
    uppercase_headings: bool = True
    pill_skills: bool = False                 # render skills as colored pill tags


@dataclass(frozen=True)
class TemplateSpec:
    id: str
    name: str
    tagline: str
    description: str
    best_for: str
    ats_score: int
    style: TemplateStyle = field(default_factory=TemplateStyle)


TEMPLATES: dict[str, TemplateSpec] = {
    "classic_pro": TemplateSpec(
        id="classic_pro",
        name="Classic Pro",
        tagline="Minimal, ATS Friendly",
        description="Clean single-column layout with crisp typography. "
                     "The safest choice for ATS parsers.",
        best_for="Any role, any experience level",
        ats_score=98,
        style=TemplateStyle(
            heading_font="Helvetica-Bold", body_font="Helvetica", docx_font="Calibri",
            header_style="plain", name_align="left", divider=True,
            uppercase_headings=True, pill_skills=False,
        ),
    ),
    "executive_elite": TemplateSpec(
        id="executive_elite",
        name="Executive Elite",
        tagline="Professional Corporate",
        description="Serif typography with a centered header and double "
                     "rule - a polished, senior look.",
        best_for="Experienced professionals, management roles",
        ats_score=93,
        style=TemplateStyle(
            heading_font="Times-Bold", body_font="Times-Roman", docx_font="Georgia",
            header_style="centered-rule", name_align="center", divider=True,
            uppercase_headings=True, pill_skills=False,
        ),
    ),
    "modern_gradient": TemplateSpec(
        id="modern_gradient",
        name="Modern Gradient",
        tagline="Modern Tech Resume",
        description="Bold accent-colored header banner with a left sidebar "
                     "accent bar - built for tech and startup roles.",
        best_for="Software / product / design roles",
        ats_score=90,
        style=TemplateStyle(
            heading_font="Helvetica-Bold", body_font="Helvetica", docx_font="Calibri",
            header_style="banner", name_align="left", divider=False,
            uppercase_headings=True, pill_skills=True,
        ),
    ),
    "campus_fresher": TemplateSpec(
        id="campus_fresher",
        name="Campus Fresher",
        tagline="Students & Freshers",
        description="Friendly, colorful accents that highlight projects and "
                     "coursework when work history is short.",
        best_for="Students, freshers, internship applicants",
        ats_score=95,
        style=TemplateStyle(
            heading_font="Helvetica-Bold", body_font="Helvetica", docx_font="Calibri",
            header_style="sidebar-bar", name_align="left", divider=True,
            uppercase_headings=False, pill_skills=True,
        ),
    ),
}

DEFAULT_TEMPLATE_ID = "classic_pro"

ACCENT_COLORS: dict[str, str] = {
    "Blue": "#2563EB",
    "Green": "#059669",
    "Purple": "#7C3AED",
    "Black": "#1F2937",
}


def get_template(template_id: str | None) -> TemplateSpec:
    """Look up a template by id, falling back to the default if unknown."""
    if not template_id or template_id not in TEMPLATES:
        return TEMPLATES[DEFAULT_TEMPLATE_ID]
    return TEMPLATES[template_id]


def list_templates() -> list[TemplateSpec]:
    return list(TEMPLATES.values())
