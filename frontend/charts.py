"""
frontend/charts.py
---------------------
Themed, reusable Plotly chart builders for the interactive dashboard.
Colors are pulled from the same design tokens as frontend/styles.py so
charts feel native to the rest of the UI, in both dark and light mode.
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

VIOLET = "#7C5CFF"
TEAL = "#22D3B0"
CORAL = "#FF6B81"
AMBER = "#FFC24B"


def _base_layout(dark: bool, title: str = "") -> dict[str, Any]:
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
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )


def readiness_gauge(percent: int, dark: bool = True) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=percent,
            number={"suffix": "%", "font": {"size": 34, "family": "Space Grotesk"}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#8A8FA3"},
                "bar": {"color": VIOLET},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 40], "color": "rgba(255,107,129,0.18)"},
                    {"range": [40, 75], "color": "rgba(255,194,75,0.18)"},
                    {"range": [75, 100], "color": "rgba(34,211,176,0.18)"},
                ],
            },
        )
    )
    fig.update_layout(**_base_layout(dark, "Career Readiness"), height=260)
    return fig


def skill_gap_bar(gaps: list[dict[str, Any]], dark: bool = True) -> go.Figure:
    skills = [g["skill"] for g in gaps]
    current = [_level_score(g["current_level"]) for g in gaps]
    required = [_level_score(g["required_level"]) for g in gaps]

    fig = go.Figure()
    fig.add_bar(name="Current Level", x=skills, y=current, marker_color=TEAL)
    fig.add_bar(name="Required Level", x=skills, y=required, marker_color=VIOLET, opacity=0.55)
    fig.update_layout(
        **_base_layout(dark, "Skill Gap: Current vs. Required"),
        barmode="group",
        height=340,
        yaxis=dict(
            **_base_layout(dark)["yaxis"],
            tickmode="array",
            tickvals=[0, 1, 2, 3],
            ticktext=["None", "Basic", "Intermediate", "Advanced"],
        ),
    )
    return fig


def weekly_effort_line(weeks: int, hours_per_week: int, dark: bool = True) -> go.Figure:
    x = list(range(1, weeks + 1))
    cumulative = [hours_per_week * w for w in x]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x, y=cumulative, mode="lines+markers", name="Cumulative Study Hours",
            line=dict(color=VIOLET, width=3, shape="spline"),
            marker=dict(size=6, color=TEAL),
            fill="tozeroy", fillcolor="rgba(124,92,255,0.12)",
        )
    )
    fig.update_layout(
        **_base_layout(dark, "Projected Cumulative Study Hours"),
        height=300,
        xaxis_title="Week", yaxis_title="Total Hours",
    )
    return fig


def progress_donut(completed: int, total: int, dark: bool = True) -> go.Figure:
    remaining = max(total - completed, 0)
    fig = go.Figure(
        go.Pie(
            labels=["Completed", "Remaining"],
            values=[completed, remaining] if total else [0, 1],
            hole=0.7,
            marker=dict(colors=[VIOLET, "rgba(138,143,163,0.25)"]),
            textinfo="none",
        )
    )
    pct = round((completed / total) * 100) if total else 0
    fig.update_layout(
        **_base_layout(dark, "Milestones Completed"),
        height=260,
        showlegend=True,
        annotations=[dict(text=f"{pct}%", x=0.5, y=0.5, font_size=26, showarrow=False,
                           font=dict(family="Space Grotesk"))],
    )
    return fig


def _level_score(level: str) -> int:
    return {"None": 0, "Basic": 1, "Intermediate": 2, "Advanced": 3}.get(level, 0)
