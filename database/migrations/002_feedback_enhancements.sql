-- ============================================================================
-- LearnMate AI — Migration 002: feedback table additions for the Admin Panel
-- Run this in the Supabase SQL Editor before using Feedback Management.
-- Idempotent-safe: checks for existing objects before altering.
-- ============================================================================

-- Phase 1's feedback table only had status in ('open','resolved'). The Admin
-- Panel spec calls for three states: Pending / Reviewed / Resolved.
alter table feedback drop constraint if exists feedback_status_check;
update feedback set status = 'pending' where status = 'open';
alter table feedback alter column status set default 'pending';
alter table feedback add constraint feedback_status_check
    check (status in ('pending', 'reviewed', 'resolved'));

-- Optional star rating (1-5), nullable — not every feedback submission needs one.
alter table feedback add column if not exists rating integer
    check (rating is null or (rating between 1 and 5));

-- ============================================================================
-- Note: no page currently lets a user SUBMIT feedback (there was none in the
-- original app either). This migration and the new Admin > Feedback page can
-- manage/display feedback rows, but the table will show an honest empty
-- state until a user-facing "Send Feedback" form is added — flagged as a
-- Phase 4 candidate rather than built here, per this phase's scope
-- (Admin Panel only, no new end-user pages).
-- ============================================================================
