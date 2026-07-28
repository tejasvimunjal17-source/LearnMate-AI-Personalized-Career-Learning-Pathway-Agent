"""
frontend/admin_export_page.py
----------------------------------
Admin Export Center (Phase 4, Part 4): a single page listing every
exportable dataset — Users, Resume Details, Resume Reviews, AI Responses,
Feedback, Notifications, Activity Logs, Analytics — each with a live
record count and one-click CSV/Excel download. Distinct from the
Database Explorer (frontend/admin_database_page.py), which is for
browsing/searching one table at a time; this page is a fast bulk-export
hub with no browsing UI of its own.
"""

from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from backend.export_data import (
    EXPORT_DATASET_LABELS,
    get_export_dataframe,
    get_export_record_count,
    ExportDataError,
)
from frontend.components import glass_card_open, glass_card_close

DATASET_ICONS = {
    "Users": "👥",
    "Resume Details": "📄",
    "Resume Reviews": "📊",
    "AI Responses": "🤖",
    "Feedback": "💬",
    "Notifications": "🔔",
    "Activity Logs": "🕒",
    "Analytics": "📈",
}


def _to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def _to_xlsx_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="export")
    return buffer.getvalue()


def render_admin_export_page() -> None:
    st.markdown("### 📦 Export Center")
    st.caption("Live counts and one-click CSV/Excel export for every dataset — no browsing needed here.")

    if st.button("🔄 Refresh Counts", key="export_center_refresh", use_container_width=False):
        st.rerun()

    st.markdown("---")

    for label in EXPORT_DATASET_LABELS:
        glass_card_open()
        icon = DATASET_ICONS.get(label, "📁")
        count = get_export_record_count(label)

        top = st.columns([3, 1])
        with top[0]:
            if count == -1:
                st.markdown(f"**{icon} {label}**")
                st.caption("⚠️ Could not load this dataset right now.")
            else:
                st.markdown(f"**{icon} {label}**")
                st.caption(f"{count} record(s)")

        if count > 0:
            try:
                df = get_export_dataframe(label)
            except ExportDataError as exc:
                st.error(f"Export failed: {exc}")
            else:
                c1, c2 = st.columns(2)
                c1.download_button(
                    "⬇️ CSV", data=_to_csv_bytes(df),
                    file_name=f"{label.lower().replace(' ', '_')}.csv",
                    mime="text/csv", use_container_width=True,
                    key=f"export_csv_{label}",
                )
                c2.download_button(
                    "⬇️ Excel", data=_to_xlsx_bytes(df),
                    file_name=f"{label.lower().replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key=f"export_xlsx_{label}",
                )
        elif count == 0:
            st.caption("Nothing to export yet.")

        glass_card_close()
