"""
frontend/profile_page.py
---------------------------
"My Profile" account page: shows the logged-in user's First Name, Last Name,
Email, and Registration Date, with Edit Profile / Logout actions.
"""

from __future__ import annotations

import streamlit as st

from backend.auth import update_user_name, RegistrationError
from backend.activity_logger import (
    log_activity, log_logout, get_resume_download_history, delete_activity_log_for_user,
)
from backend.supabase_client import _get_client, SupabaseUnavailableError
from backend.resume_store import _from_db_row as _resume_from_db_row
from backend.resume_generator import build_resume_pdf, build_resume_docx, ResumeGenerationError
from backend.resume_details import delete_by_id_for_user as delete_resume_for_user
from backend.roadmap_store import delete_roadmap_for_user
from backend.ai_response_store import delete_ai_response_for_user
from frontend.components import hero, glass_card_open, glass_card_close, metric_card

HISTORY_PAGE_SIZE = 5


def _resolve_user_id(client, email: str) -> str | None:
    email_norm = (email or "").strip().lower()
    if not email_norm:
        return None
    resp = client.table("users").select("id").eq("email", email_norm).limit(1).execute()
    rows = resp.data or []
    return rows[0]["id"] if rows else None


def _empty(message: str) -> None:
    st.markdown(f"<p class='muted'>{message}</p>", unsafe_allow_html=True)


def _paginate(rows: list[dict], key_prefix: str) -> tuple[list[dict], int, int]:
    """Returns (page_rows, current_page, total_pages) for a HISTORY_PAGE_SIZE-item page."""
    total = len(rows)
    total_pages = max(1, (total - 1) // HISTORY_PAGE_SIZE + 1)
    page = st.number_input(
        "Page", min_value=1, max_value=total_pages, value=1, step=1, key=f"{key_prefix}_page",
    )
    start = (page - 1) * HISTORY_PAGE_SIZE
    return rows[start:start + HISTORY_PAGE_SIZE], page, total_pages


def _confirm_delete(item_id: str, key_prefix: str, on_confirm) -> None:
    """Two-step delete: first click asks for confirmation, second click
    (Yes, delete) actually calls on_confirm(). Prevents accidental deletes."""
    confirm_key = f"{key_prefix}_confirm_{item_id}"
    if st.session_state.get(confirm_key):
        st.warning("Delete this permanently? This can't be undone.")
        yes_col, no_col = st.columns(2)
        if yes_col.button("✅ Yes, delete", key=f"{key_prefix}_yes_{item_id}", use_container_width=True):
            try:
                on_confirm()
                st.session_state[confirm_key] = False
                st.success("Deleted.")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Couldn't delete: {exc}")
        if no_col.button("Cancel", key=f"{key_prefix}_no_{item_id}", use_container_width=True):
            st.session_state[confirm_key] = False
            st.rerun()
    else:
        if st.button("🗑️ Delete", key=f"{key_prefix}_del_{item_id}", use_container_width=True):
            st.session_state[confirm_key] = True
            st.rerun()


def _render_resume_history_tab(user_id: str, email: str) -> None:
    try:
        client = _get_client()
        resp = (
            client.table("resume_details")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        rows = resp.data or []
    except Exception as exc:  # noqa: BLE001
        st.error(f"⚠️ Could not load resume history: {exc}")
        return

    if not rows:
        _empty("No saved resumes yet. Build one from the **Resume Builder** page.")
        return

    search = st.text_input(
        "🔎 Search by name, education, or skill", key="resume_hist_search", placeholder="e.g. Python, MBA…"
    )
    if search:
        term = search.lower()
        rows = [
            r for r in rows
            if term in f"{r.get('first_name','')} {r.get('last_name','')}".lower()
            or term in (r.get("education") or "").lower()
            or term in ", ".join(r.get("skills") or []).lower()
        ]

    st.caption(f"**{len(rows)}** saved resume(s)")
    if not rows:
        _empty("No resumes match your search.")
        return

    page_rows, page, total_pages = _paginate(rows, "resume_hist")

    for row in page_rows:
        profile = _resume_from_db_row(row, email)
        saved_on = str(row.get("created_at", ""))[:19]
        with st.expander(f"📄 {profile.full_name} — {saved_on}"):
            st.markdown(f"**Education:** {profile.education or '—'}")
            st.markdown(f"**Skills:** {', '.join(profile.skills) or '—'}")
            if profile.projects:
                st.markdown(f"**Projects:** {', '.join(p.title for p in profile.projects if p.title)}")
            if profile.certificates:
                st.markdown(f"**Certificates:** {', '.join(c.name for c in profile.certificates if c.name)}")

            d1, d2 = st.columns(2)
            try:
                pdf_bytes = build_resume_pdf(profile)
                d1.download_button(
                    "⬇️ Download PDF", data=pdf_bytes,
                    file_name=f"{profile.full_name.replace(' ', '_')}_{saved_on[:10]}.pdf",
                    mime="application/pdf", use_container_width=True,
                    key=f"resume_hist_pdf_{row['id']}",
                    on_click=log_activity, args=(email, "resume_download"),
                )
            except ResumeGenerationError as exc:
                d1.error(f"Couldn't regenerate PDF: {exc}")

            try:
                docx_bytes = build_resume_docx(profile)
                d2.download_button(
                    "⬇️ Download DOCX", data=docx_bytes,
                    file_name=f"{profile.full_name.replace(' ', '_')}_{saved_on[:10]}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    key=f"resume_hist_docx_{row['id']}",
                    on_click=log_activity, args=(email, "resume_download"),
                )
            except ResumeGenerationError as exc:
                d2.error(f"Couldn't regenerate DOCX: {exc}")

            _confirm_delete(row["id"], "resume_hist", lambda rid=row["id"]: delete_resume_for_user(rid, user_id))

    st.caption(f"Page {page} of {total_pages}")


def _render_resume_downloads_tab(user_id: str) -> None:
    rows = get_resume_download_history(user_id)

    if not rows:
        _empty("No resume downloads logged yet.")
        return

    search = st.text_input("🔎 Search by date", key="dl_hist_search", placeholder="e.g. 2026-07…")
    if search:
        rows = [r for r in rows if search in str(r.get("created_at", ""))]

    st.caption(f"**{len(rows)}** download(s) logged")
    if not rows:
        _empty("No downloads match your search.")
        return

    import io
    import csv as csv_module

    buffer = io.StringIO()
    writer = csv_module.writer(buffer)
    writer.writerow(["Downloaded At"])
    for r in rows:
        writer.writerow([str(r.get("created_at", ""))[:19]])
    st.download_button(
        "⬇️ Download this list as CSV", data=buffer.getvalue(), file_name="resume_download_history.csv",
        mime="text/csv", key="dl_hist_csv",
    )

    page_rows, page, total_pages = _paginate(rows, "dl_hist")
    for row in page_rows:
        c1, c2 = st.columns([4, 1])
        c1.markdown(f"⬇️ Resume downloaded at **{str(row.get('created_at',''))[:19]}**")
        with c2:
            _confirm_delete(row["id"], "dl_hist", lambda rid=row["id"]: delete_activity_log_for_user(rid, user_id))
    st.caption(f"Page {page} of {total_pages}")


def _render_ai_history_tab(user_id: str) -> None:
    try:
        client = _get_client()
        resp = (
            client.table("ai_responses")
            .select("id, prompt, response, model, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        rows = resp.data or []
    except Exception as exc:  # noqa: BLE001
        st.error(f"⚠️ Could not load AI history: {exc}")
        return

    if not rows:
        _empty("No AI Mentor conversations logged yet. Try the chat widget on any page.")
        return

    search = st.text_input("🔎 Search your questions/replies", key="ai_hist_search", placeholder="e.g. resume, interview…")
    models = sorted({r.get("model") for r in rows if r.get("model")})
    model_filter = st.selectbox("Filter by model", options=["(all)"] + models, key="ai_hist_model_filter")

    if search:
        term = search.lower()
        rows = [r for r in rows if term in (r.get("prompt", "") + r.get("response", "")).lower()]
    if model_filter != "(all)":
        rows = [r for r in rows if r.get("model") == model_filter]

    st.caption(f"**{len(rows)}** conversation(s)")
    if not rows:
        _empty("No conversations match your search/filter.")
        return

    page_rows, page, total_pages = _paginate(rows, "ai_hist")

    for row in page_rows:
        timestamp = str(row.get("created_at", ""))[:19]
        with st.expander(f"🤖 {timestamp}" + (f" · {row['model']}" if row.get("model") else "")):
            st.markdown(f"**You asked:** {row.get('prompt', '')}")
            st.markdown(f"**AI Mentor replied:** {row.get('response', '')}")
            export_text = f"You: {row.get('prompt','')}\n\nAI Mentor: {row.get('response','')}"
            st.download_button(
                "⬇️ Download this exchange (.txt)", data=export_text,
                file_name=f"ai_chat_{timestamp[:10]}.txt", mime="text/plain",
                key=f"ai_hist_dl_{row['id']}",
            )
            _confirm_delete(row["id"], "ai_hist", lambda rid=row["id"]: delete_ai_response_for_user(rid, user_id))

    st.caption(f"Page {page} of {total_pages}")


def _render_roadmap_history_tab(user_id: str) -> None:
    try:
        client = _get_client()
        resp = (
            client.table("roadmaps")
            .select("id, career_goal, estimated_timeline, certifications, projects, is_offline_fallback, roadmap_json, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        rows = resp.data or []
    except Exception as exc:  # noqa: BLE001
        st.error(f"⚠️ Could not load roadmap history: {exc}")
        return

    if not rows:
        _empty("No roadmaps generated yet. Fill out the **Career Profile** form to get one.")
        return

    search = st.text_input("🔎 Search by career goal", key="roadmap_hist_search", placeholder="e.g. Data Analyst…")
    if search:
        term = search.lower()
        rows = [r for r in rows if term in (r.get("career_goal") or "").lower()]

    st.caption(f"**{len(rows)}** roadmap(s)")
    if not rows:
        _empty("No roadmaps match your search.")
        return

    page_rows, page, total_pages = _paginate(rows, "roadmap_hist")

    import json as json_module

    for row in page_rows:
        timestamp = str(row.get("created_at", ""))[:19]
        with st.expander(f"🧭 {row.get('career_goal', 'Roadmap')} — {timestamp}"):
            st.markdown(f"**Estimated Timeline:** {row.get('estimated_timeline') or '—'}")
            certs = row.get("certifications") or []
            projects = row.get("projects") or []
            st.markdown(f"**Certifications:** {', '.join(certs) if certs else '—'}")
            st.markdown(f"**Projects:** {', '.join(projects) if projects else '—'}")
            if row.get("is_offline_fallback"):
                st.caption("Generated offline (AI service unavailable at the time).")

            st.download_button(
                "⬇️ Download full roadmap (.json)",
                data=json_module.dumps(row.get("roadmap_json") or {}, indent=2),
                file_name=f"roadmap_{timestamp[:10]}.json", mime="application/json",
                key=f"roadmap_hist_dl_{row['id']}",
            )
            _confirm_delete(row["id"], "roadmap_hist", lambda rid=row["id"]: delete_roadmap_for_user(rid, user_id))

    st.caption(f"Page {page} of {total_pages}")


def render_profile_page() -> None:
    user = st.session_state.get("auth_user")
    if not user:
        st.warning("You need to register or log in first.")
        return

    hero("My Profile", f"{user['first_name']} {user['last_name']}", "Your LearnMate AI account details.")

    c1, c2, c3 = st.columns(3)
    metric_card("Email", user["email"], c1)
    metric_card("Registered On", user.get("registration_date", "-"), c2)
    metric_card("Roadmap Status", "Generated ✅" if st.session_state.get("roadmap") else "Not started", c3)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    glass_card_open("✏️ Edit Profile")
    with st.form("edit_profile_form"):
        c1, c2 = st.columns(2)
        new_first = c1.text_input("First Name", value=user["first_name"])
        new_last = c2.text_input("Last Name", value=user["last_name"])
        st.text_input("Email Address", value=user["email"], disabled=True, help="Email can't be changed — it's your account identifier.")
        save = st.form_submit_button("💾 Save Changes", use_container_width=True)
    glass_card_close()

    if save:
        try:
            update_user_name(user["email"], new_first, new_last)
            st.session_state["auth_user"]["first_name"] = new_first.strip()
            st.session_state["auth_user"]["last_name"] = new_last.strip()
            log_activity(user["email"], "profile_update")
            st.success("✅ Profile updated.")
            st.rerun()
        except RegistrationError as exc:
            st.error(str(exc))

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    if st.button("🚪 Logout", key="profile_logout", use_container_width=True):
        log_activity(user["email"], "logout")
        log_logout(st.session_state.get("login_log_id"))
        for key in ["auth_user", "profile", "roadmap", "completed_weeks", "login_log_id"]:
            st.session_state.pop(key, None)
        st.session_state["landing_view"] = "home"
        st.session_state["page"] = "Career Profile"
        st.rerun()

    # ------------------------------------------------------------------
    # History tabs (Phase 4) — read-only, straight from Supabase.
    # ------------------------------------------------------------------
    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
    st.markdown("### 🗂️ Your History")

    try:
        client = _get_client()
        user_id = _resolve_user_id(client, user["email"])
    except SupabaseUnavailableError as exc:
        st.error(f"⚠️ History is unavailable right now: {exc}")
        return

    if not user_id:
        _empty("History isn't available for this account yet.")
        return

    tab_resume, tab_downloads, tab_ai, tab_roadmap = st.tabs(
        ["📄 Resume History", "⬇️ Resume Downloads", "🤖 AI History", "🧭 Roadmap History"]
    )
    with tab_resume:
        _render_resume_history_tab(user_id, user["email"])
    with tab_downloads:
        _render_resume_downloads_tab(user_id)
    with tab_ai:
        _render_ai_history_tab(user_id)
    with tab_roadmap:
        _render_roadmap_history_tab(user_id)
