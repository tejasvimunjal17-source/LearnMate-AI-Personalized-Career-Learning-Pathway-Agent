-- ============================================================================
-- LearnMate AI — Migration 010: Resume Settings additions for the new
-- Resume Builder (template gallery / AI toolkit / Professional Summary).
-- Run this in the Supabase SQL Editor before deploying the updated
-- backend/resume_store.py.
--
-- PURELY ADDITIVE. No existing column is renamed, retyped, or dropped:
--   - `resume_template` (added in sql/003_resume_details_additions.sql)
--     is REUSED as-is for the new template picker - see the mapping note
--     in backend/resume_store.py (profile.template_id <-> db column
--     resume_template). It is NOT touched by this migration.
--   - first_name, last_name, education, skills, certificates,
--     internships, projects, achievements, hobbies, pdf_path, docx_path,
--     created_at, updated_at, user_id, id: all untouched.
-- Existing rows keep all their existing data; the six new columns below
-- simply default in for rows saved before this migration.
-- ============================================================================

alter table resume_details add column if not exists accent_color text default '#2563EB';
alter table resume_details add column if not exists target_role text default '';
alter table resume_details add column if not exists experience_level text default 'Fresher';
alter table resume_details add column if not exists summary text default '';
alter table resume_details add column if not exists one_page boolean default true;
alter table resume_details add column if not exists show_photo boolean default false;

-- ============================================================================
-- Verification query (optional) - confirms every ResumeProfile field now
-- has a matching column, run this after applying the migration:
--
-- select column_name, data_type, column_default
-- from information_schema.columns
-- where table_name = 'resume_details'
-- order by ordinal_position;
--
-- Expected columns (order may vary): id, user_id, first_name, last_name,
-- education, skills, certificates, internships, projects, achievements,
-- hobbies, created_at, updated_at, pdf_path, docx_path, resume_template,
-- accent_color, target_role, experience_level, summary, one_page,
-- show_photo.
-- ============================================================================
