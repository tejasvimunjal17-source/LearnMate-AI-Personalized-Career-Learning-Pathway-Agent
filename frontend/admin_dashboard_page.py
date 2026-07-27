"""
frontend/admin_dashboard_page.py
------------------------------------
Admin Dashboard: KPI cards + Plotly charts, sourced entirely from live
Supabase data via backend.admin_data.get_dashboard_stats(). No numbers
are ever fabricated — if Supabase can't be reached, an honest error is
shown instead of zeros or placeholder charts.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from backend.admin_data import get_dashboard_stats, AdminDataError
from frontend.components import glass_card_open, glass_card_close, metric_card

VIOLET = "#7C5CFF"
TEAL = "#22D3B0"
CORAL = "#FF6B81"
AMBER = "#FFC24B"
SLATE = "#5B6079"


def _chart_layout(dark: bool, title: str) -> dict:
    text_color = "#EDEEFB" if dark else "#1B1E33"
    grid_color = "rgba(255,255,255,0.08)" if dark else "rgba(15,18,41,0.08)"
    return dict(
        title=dict(text=title, font=dict(family="Space Grotesk, sans-serif", size=16, color=text_color)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=text_color),
        margin=dict(l=10, r=10, t=48, b=10),
        xaxis=dict(gridcolor=grid_color, zerolinecolor=grid_color),
        yaxis=dict(gridcolor=grid_color, zerolinecolor=grid_color),
        height=320,
    )


def _signups_trend_chart(signups: list[dict], dark: bool) -> go.Figure:
    dates = [row["date"] for row in signups]
    counts = [row["count"] for row in signups]
    fig = go.Figure(
        go.Scatter(
            x=dates,
            y=counts,
            mode="lines+markers",
            line=dict(color=VIOLET, width=3),
            marker=dict(color=TEAL, size=7),
            fill="tozeroy",
            fillcolor="rgba(124,92,255,0.12)",
        )
    )
    layout = _chart_layout(dark, "New Registrations — Last 14 Days")
    layout["yaxis"]["dtick"] = 1
    fig.update_layout(**layout)
    return fig


def _activity_mix_chart(stats, dark: bool) -> go.Figure:
    labels = ["Resume Details", "Resume Reviews", "Roadmap Requests", "Generated Roadmaps", "AI Responses"]
    values = [
        stats.total_resume_details,
        stats.total_resume_reviews,
        stats.total_roadmap_requests,
        stats.total_generated_roadmaps,
        stats.total_ai_responses,
    ]
    fig = go.Figure(go.Bar(x=labels, y=values, marker_color=[VIOLET, TEAL, CORAL, AMBER, SLATE]))
    fig.update_layout(**_chart_layout(dark, "Platform Activity Mix"))
    return fig


def render_admin_dashboard_page() -> None:
    """Render the full Admin Dashboard: KPI cards, charts, recent registrations."""
    dark = st.session_state.get("dark_mode", True)

    try:
        stats = get_dashboard_stats()
    except AdminDataError as exc:
        st.error(f"⚠️ Could not load dashboard data: {exc}")
        return

    st.markdown("### 📊 Overview")

    row1 = st.columns(4)
    metric_card("Total Users", str(stats.total_users), row1[0])
    metric_card("Resume Details", str(stats.total_resume_details), row1[1])
    metric_card("Resume Reviews", str(stats.total_resume_reviews), row1[2])
    metric_card("Roadmap Requests", str(stats.total_roadmap_requests), row1[3])

    row2 = st.columns(3)
    metric_card("Generated Roadmaps", str(stats.total_generated_roadmaps), row2[0])
    metric_card("AI Responses", str(stats.total_ai_responses), row2[1])
    metric_card("Feedback Count", str(stats.total_feedback), row2[2])

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(_signups_trend_chart(stats.signups_last_14_days, dark), use_container_width=True)
    with c2:
        st.plotly_chart(_activity_mix_chart(stats, dark), use_container_width=True)

    st.markdown("---")
    st.markdown("### 🆕 Recent Registrations")
    glass_card_open()
    if not stats.recent_registrations:
        st.markdown("<p class='muted'>No registrations yet.</p>", unsafe_allow_html=True)
    else:
        for r in stats.recent_registrations:
            st.markdown(
                f"**{r.get('first_name', '')} {r.get('last_name', '')}** · "
                f"<span class='muted'>{r.get('email', '')}</span> · "
                f"<span class='mono muted' style='font-size:0.8rem;'>{(r.get('created_at') or '')[:10]}</span>",
                unsafe_allow_html=True,
            )
    glass_card_close()
