-- ============================================================================
-- LearnMate AI — Migration 004: ai_responses additions for Phase 4
-- Run this in the Supabase SQL Editor before deploying
-- backend/ai_response_store.py.
-- ============================================================================

alter table ai_responses add column if not exists model text default '';
alter table ai_responses add column if not exists tokens_used integer;
alter table ai_responses add column if not exists response_time_ms integer;

-- ============================================================================
-- Note: tokens_used stays NULL unless the AI provider's response includes
-- usage data AND the calling code captures it. As of this migration,
-- backend/openrouter_client.py's generate_chat_response() returns only the
-- reply text (its existing, unchanged public contract), so tokens_used is
-- not currently populated - left NULL rather than fabricated. model and
-- response_time_ms ARE populated (from config and a wall-clock timer,
-- respectively) by frontend/chatbot.py at save time.
-- ============================================================================
