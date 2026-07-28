"""
frontend/admin_database_page.py
------------------------------------
Database Explorer: one sub-tab per Supabase table, each a searchable,
sortable, filterable, paginated table with a live row count, a manual
Refresh control, and CSV / Excel export — reading real data only, via
backend.admin_data.fetch_table_df() (no direct DB calls here).

Note on "Refresh": there is no caching layer anywhere in this page —
fetch_table_df() queries Supabase fresh on every Streamlit rerun already.
The Refresh button doesn't bypass a cache (there isn't one to bypass); it
gives the admin an explicit, obvious way to force a new fetch (e.g. after
making a change on another tab) without hunting for an unrelated widget
to nudge.
"""

from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from backend.admin_data import fetch_table_df, AdminDataError
from frontend.components import glass_card_open, glass_card_close

# Display label (as requested) -> underlying backend.admin_data.DB_TABLES key
TAB_LABEL_TO_DB_KEY: dict[str, str] = {
    "Users": "Users Data",
    "Resume Details": "Resume Details",
    "Resume Reviews": "Resume Reviews",
    "Roadmap Requests": "Roadmap Requests",
    "Generated Roadmaps": "Generated Roadmaps",
    "AI Responses": "AI Responses",
    "Feedback": "Feedback",
    "Login Logs": "Login Logs",
    "User Activity": "User Activity Logs",
    "Announcements": "Announcements",
    "Notifications": "Notifications",
}


def _to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def _to_xlsx_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="data")
    return buffer.getvalue()


def _render_table_tab(label: str, key_prefix: str) -> None:
    top_bar = st.columns([5, 1])
    if top_bar[1].button("🔄 Refresh", key=f"{key_prefix}_refresh", use_container_width=True):
        st.rerun()

    try:
        df = fetch_table_df(TAB_LABEL_TO_DB_KEY[label])
    except AdminDataError as exc:
        st.error(f"⚠️ Could not load '{label}': {exc}")
        return

    glass_card_open(label)

    if df.empty:
        st.markdown(f"<p class='muted'>No rows in '{label}' yet.</p>", unsafe_allow_html=True)
        glass_card_close()
        return

    st.caption(f"**{len(df)}** total record(s) in this table.")

    # --- Search ---
    search_term = st.text_input(
        "🔎 Search", key=f"{key_prefix}_search", placeholder="Search all columns…"
    )
    working_df = df
    if search_term:
        mask = working_df.apply(
            lambda row: row.astype(str).str.contains(search_term, case=False, na=False).any(), axis=1
        )
        working_df = working_df[mask]

    # --- Filter (by a chosen column's value) ---
    filter_cols = st.columns([1, 1, 1, 1])
    filter_column = filter_cols[0].selectbox(
        "Filter column", options=["(none)"] + list(df.columns), key=f"{key_prefix}_filter_col"
    )
    if filter_column != "(none)":
        unique_vals = ["(all)"] + sorted(working_df[filter_column].dropna().astype(str).unique().tolist())
        filter_value = filter_cols[1].selectbox(
            "Filter value", options=unique_vals, key=f"{key_prefix}_filter_val"
        )
        if filter_value != "(all)":
            working_df = working_df[working_df[filter_column].astype(str) == filter_value]

    # --- Sort ---
    sort_col = filter_cols[2].selectbox(
        "Sort by", options=list(df.columns), key=f"{key_prefix}_sort_col"
    )
    sort_dir = filter_cols[3].selectbox(
        "Order", options=["Descending", "Ascending"], key=f"{key_prefix}_sort_dir"
    )
    working_df = working_df.sort_values(by=sort_col, ascending=(sort_dir == "Ascending"), kind="stable")

    # --- Row count + pagination ---
    total_rows = len(working_df)
    st.caption(f"**{total_rows}** row(s) match the current search/filter (of {len(df)} total).")

    page_size = 15
    total_pages = max(1, (total_rows - 1) // page_size + 1)
    page = st.number_input(
        "Page", min_value=1, max_value=total_pages, value=1, step=1, key=f"{key_prefix}_page"
    )
    start = (page - 1) * page_size
    end = start + page_size

    st.dataframe(working_df.iloc[start:end], use_container_width=True, hide_index=True)
    st.caption(f"Page {page} of {total_pages}")

    # --- Export (full filtered/sorted result set, not just the current page) ---
    c1, c2 = st.columns(2)
    c1.download_button(
        "⬇️ Download CSV",
        data=_to_csv_bytes(working_df),
        file_name=f"{key_prefix}.csv",
        mime="text/csv",
        use_container_width=True,
        key=f"{key_prefix}_csv",
    )
    c2.download_button(
        "⬇️ Download Excel",
        data=_to_xlsx_bytes(working_df),
        file_name=f"{key_prefix}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key=f"{key_prefix}_xlsx",
    )

    glass_card_close()


def render_admin_database_page() -> None:
    """Render the full Database Explorer: one sub-tab per table."""
    st.markdown("### 🗄️ Database Explorer")
    st.caption("Read-only, spreadsheet-style view of every table — live from Supabase.")

    labels = list(TAB_LABEL_TO_DB_KEY.keys())
    tabs = st.tabs(labels)

    for label, tab in zip(labels, tabs):
        with tab:
            _render_table_tab(label, key_prefix=f"dbexp_{label.lower().replace(' ', '_')}")
