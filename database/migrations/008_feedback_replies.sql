-- ============================================================================
-- LearnMate AI — Migration 008: feedback_replies (Phase 4, Part 1)
-- Run this in the Supabase SQL Editor before deploying the updated
-- backend/admin_data.py / frontend/admin_feedback_page.py.
--
-- A separate table (not a single "reply" column on feedback) so a
-- feedback item can have a full reply thread/history, not just one reply.
-- ============================================================================

create table if not exists feedback_replies (
    id              uuid primary key default gen_random_uuid(),
    feedback_id     uuid not null references feedback(id) on delete cascade,
    admin_id        uuid references admin_users(id) on delete set null,
    reply_text      text not null,
    created_at      timestamptz not null default now()
);
create index if not exists idx_feedback_replies_feedback_id on feedback_replies (feedback_id);
create index if not exists idx_feedback_replies_created_at on feedback_replies (created_at desc);

alter table feedback_replies enable row level security;
