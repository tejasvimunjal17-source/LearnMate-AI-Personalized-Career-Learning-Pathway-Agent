-- ============================================================================
-- LearnMate AI — Migration 009: Analytics Dashboard indexes (Phase 4, Part 2)
-- Run this in the Supabase SQL Editor before deploying
-- backend/analytics_data.py.
--
-- Only two indexes are added here, and only because the new analytics
-- queries introduce two filter patterns not covered by Phase 1's existing
-- indexes (which only cover user_id/admin_id/created_at):
--   1. user_activity_logs.activity_type - every feature-usage stat
--      (get_resume_stats, get_ai_roadmap_stats, get_ai_chatbot_stats, ...)
--      filters on an exact activity_type match.
--   2. login_logs.user_type - get_active_user_counts() and get_login_trend()
--      both filter to user_type = 'user' before their date-range filter.
-- No other new indexes were added - the rest of this module's queries
-- (feedback, notifications, resume_reviews, roadmaps, ai_responses) are
-- either full-table scans over small tables or already covered by
-- existing primary-key/created_at indexes from sql/001_init_schema.sql.
-- ============================================================================

create index if not exists idx_activity_logs_activity_type on user_activity_logs (activity_type);
create index if not exists idx_login_logs_user_type on login_logs (user_type);
