"""
frontend/admin_analytics_page.py
-------------------------------------
Advanced Analytics Dashboard (Phase 4, Part 2): DAU/WAU/MAU, registration
and login trends, per-feature usage statistics, feedback/notification
stats, most active users, recent activity, and the Admin Audit Log
summary — all sourced from backend.analytics_data.get_analytics_snapshot(),
which reads Supabase only. No fabricated numbers anywhere on this page.

Distinct from frontend/admin_dashboard_page.py (Phase 3's simpler KPI
dashboard), which is untouched by this file.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from backend.analytics_data import get_analytics_snapshot, AnalyticsError
from frontend.components import glass_card_open, glass_card_close, metric_card

VIOLET = "#7C5CFF"
TEAL = "#22D3B0"
CORAL = "#FF6B81"
AMBER = "#FFC24B"
SLATE = "#5B6079"


def _chart_layout(dark: bool, title: str, height: int = 300) -> dict:
    text_color = "#EDEEFB" if dark else "#1B1E33"
    grid_color = "rgba(255,255,255,0.08)" if dark else "rgba(15,18,41,0.08)"
    return dict(
        title=dict(text=title, font=dict(family="Space Grotesk, sans-serif", size=15, color=text_color)),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=text_color),
        margin=dict(l=10, r=10, t=44, b=10),
        xaxis=dict(gridcolor=grid_color, zerolinecolor=grid_color),
        yaxis=dict(gridcolor=grid_color, zerolinecolor=grid_color, dtick=1),
        height=height,
    )


def _hex_to_rgba(hex_color: str, alpha: float = 0.12) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _trend_chart(series: list[dict], dark: bool, title: str, color: str) -> go.Figure:
    dates = [row["date"] for row in series]
    counts = [row["count"] for row in series]
    fig = go.Figure(
        go.Scatter(
            x=dates, y=counts, mode="lines+markers",
            line=dict(color=color, width=3), marker=dict(color=color, size=6),
            fill="tozeroy", fillcolor=_hex_to_rgba(color),
        )
    )
    fig.update_layout(**_chart_layout(dark, title))
    return fig


def _bar_chart(labels: list[str], values: list[int], dark: bool, title: str, colors: list[str]) -> go.Figure:
    fig = go.Figure(go.Bar(x=labels, y=values, marker_color=colors))
    fig.update_layout(**_chart_layout(dark, title))
    return fig


def render_admin_analytics_page() -> None:
    st.markdown("### 📈 Advanced Analytics")
    dark = st.session_state.get("dark_mode", True)

    try:
        snap = get_analytics_snapshot()
    except AnalyticsError as exc:
        st.error(f"⚠️ Could not load analytics: {exc}")
        return

    # --- Active users ---
    st.markdown("#### 👥 Active Users")
    c1, c2, c3, c4 = st.columns(4)
    metric_card("Daily Active Users", str(snap.active_users.get("dau", 0)), c1)
    metric_card("Weekly Active Users", str(snap.active_users.get("wau", 0)), c2)
    metric_card("Monthly Active Users", str(snap.active_users.get("mau", 0)), c3)
    metric_card("Total Registrations", str(snap.total_registrations), c4)
    st.caption(
        "DAU/WAU/MAU are distinct users with a logged login in the last 1/7/30 days — "
        "these will be sparse until login activity has had time to accumulate."
    )

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(_trend_chart(snap.registration_trend, dark, "Registration Trend (14 days)", VIOLET), use_container_width=True)
    with c2:
        st.plotly_chart(_trend_chart(snap.login_trend, dark, "Login Trend (14 days)", TEAL), use_container_width=True)

    # --- Feature usage ---
    st.markdown("---")
    st.markdown("#### 🧩 Feature Usage")
    c1, c2, c3, c4 = st.columns(4)
    metric_card("Resumes Saved", str(snap.resume_stats.get("total_saved", 0)), c1)
    metric_card("Resume Reviews", str(snap.resume_review_stats.get("total_reviews", 0)), c2)
    metric_card("Roadmaps Generated", str(snap.ai_roadmap_stats.get("total_roadmaps", 0)), c3)
    metric_card("AI Chat Exchanges", str(snap.ai_chatbot_stats.get("total_exchanges", 0)), c4)

    avg_score = snap.resume_review_stats.get("average_score")
    c5, c6 = st.columns(2)
    metric_card("Avg. Resume Score", f"{avg_score}" if avg_score is not None else "—", c5)
    metric_card("AI Roadmap Generation Events", str(snap.ai_roadmap_stats.get("generation_events", 0)), c6)

    st.plotly_chart(
        _bar_chart(
            ["Resume Gen.", "Resume DL", "Resume Review", "AI Roadmap", "AI Chat"],
            [
                snap.resume_stats.get("generation_events", 0),
                snap.resume_stats.get("download_events", 0),
                snap.resume_review_stats.get("total_reviews", 0),
                snap.ai_roadmap_stats.get("generation_events", 0),
                snap.ai_chatbot_stats.get("usage_events", 0),
            ],
            dark, "Feature Usage Events", [VIOLET, TEAL, CORAL, AMBER, SLATE],
        ),
        use_container_width=True,
    )

    # --- Feedback & notifications ---
    st.markdown("---")
    st.markdown("#### 💬 Feedback & 🔔 Notifications")
    fb = snap.feedback_stats
    notif = snap.notification_stats
    c1, c2, c3, c4 = st.columns(4)
    metric_card("Total Feedback", str(fb.get("total", 0)), c1)
    avg_rating = fb.get("average_rating")
    metric_card("Avg. Rating", f"{avg_rating} ⭐" if avg_rating is not None else "—", c2)
    metric_card("Notifications Sent", str(notif.get("total", 0)), c3)
    metric_card("Notification Reads", str(notif.get("total_reads", 0)), c4)

    c1, c2 = st.columns(2)
    with c1:
        by_status = fb.get("by_status", {})
        if by_status:
            st.plotly_chart(
                _bar_chart(list(by_status.keys()), list(by_status.values()), dark, "Feedback by Status", [AMBER, TEAL, VIOLET]),
                use_container_width=True,
            )
        else:
            st.caption("No feedback yet.")
    with c2:
        by_category = fb.get("by_category", {})
        if by_category:
            st.plotly_chart(
                _bar_chart(list(by_category.keys()), list(by_category.values()), dark, "Feedback by Category", [VIOLET, CORAL, TEAL]),
                use_container_width=True,
            )
        else:
            st.caption("No feedback yet.")

    # --- Most active users ---
    st.markdown("---")
    st.markdown("#### 🏆 Most Active Users")
    glass_card_open()
    if not snap.most_active_users:
        st.markdown("<p class='muted'>No activity logged yet.</p>", unsafe_allow_html=True)
    else:
        for u in snap.most_active_users:
            st.markdown(
                f"**{u['name'] or u['email']}** · <span class='muted'>{u['email']}</span> · "
                f"<span class='mono'>{u['activity_count']} actions</span>",
                unsafe_allow_html=True,
            )
    glass_card_close()

    # --- Recent activity ---
    st.markdown("---")
    st.markdown("#### 🕒 Recent Activity")
    glass_card_open()
    if not snap.recent_activity:
        st.markdown("<p class='muted'>No activity logged yet.</p>", unsafe_allow_html=True)
    else:
        for a in snap.recent_activity:
            email = (a.get("users") or {}).get("email", "—") if isinstance(a.get("users"), dict) else "—"
            st.markdown(
                f"<span class='mono muted' style='font-size:0.8rem;'>{str(a.get('created_at',''))[:19]}</span> "
                f"— **{a.get('activity_type','')}** by {email}",
                unsafe_allow_html=True,
            )
    glass_card_close()

    # --- Admin audit log summary ---
    st.markdown("---")
    st.markdown("#### 🛡️ Admin Activity Summary")
    admin_activity = snap.admin_activity
    by_type = admin_activity.get("by_type", {})
    if by_type:
        st.plotly_chart(
            _bar_chart(list(by_type.keys()), list(by_type.values()), dark, "Admin Actions by Type", [VIOLET, TEAL, CORAL, AMBER, SLATE]),
            use_container_width=True,
        )
    glass_card_open("Recent Admin Actions")
    recent_admin = admin_activity.get("recent", [])
    if not recent_admin:
        st.markdown("<p class='muted'>No admin actions logged yet.</p>", unsafe_allow_html=True)
    else:
        for a in recent_admin:
            admin_email = (a.get("admin_users") or {}).get("email", "—") if isinstance(a.get("admin_users"), dict) else "—"
            st.markdown(
                f"<span class='mono muted' style='font-size:0.8rem;'>{str(a.get('created_at',''))[:19]}</span> "
                f"— **{a.get('activity_type','')}** by {admin_email}",
                unsafe_allow_html=True,
            )
    glass_card_close()
