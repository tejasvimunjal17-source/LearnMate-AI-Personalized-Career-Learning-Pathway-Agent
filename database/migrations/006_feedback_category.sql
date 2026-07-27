-- ============================================================================
-- LearnMate AI — Migration 006: feedback.category for the User Feedback module
-- Run this in the Supabase SQL Editor before deploying
-- backend/feedback_store.py / frontend/feedback_page.py.
-- ============================================================================

alter table feedback add column if not exists category text default 'general';
update feedback set category = 'general' where category is null;
alter table feedback drop constraint if exists feedback_category_check;
alter table feedback add constraint feedback_category_check
    check (category in ('general', 'bug', 'feature'));
