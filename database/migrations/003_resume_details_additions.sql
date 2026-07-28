-- ============================================================================
-- LearnMate AI — Migration 003: resume_details additions for Phase 4
-- Run this in the Supabase SQL Editor before deploying the updated
-- backend/resume_store.py / backend/resume_details.py.
-- ============================================================================

alter table resume_details add column if not exists resume_template text default '';
alter table resume_details add column if not exists pdf_path text default '';
alter table resume_details add column if not exists docx_path text default '';

-- ============================================================================
-- Note on pdf_path / docx_path: the Resume Builder currently generates PDF
-- and DOCX files entirely in memory (backend/resume_generator.py returns
-- bytes straight to st.download_button) and never writes them to a path
-- anywhere - on Streamlit Cloud there is no durable filesystem to write to
-- in the first place. These columns exist so a path CAN be recorded once
-- generated files are uploaded somewhere durable (e.g. Supabase Storage),
-- but no current code path populates them yet. They default to '' rather
-- than being fabricated, consistent with the app's existing "no fake data"
-- principle. Wiring actual file storage + these paths is future work,
-- outside backend/resume_store.py's scope (would touch resume_generator.py
-- and/or resume_builder.py, not requested this phase).
-- ============================================================================
