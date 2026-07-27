-- ============================================================================
-- LearnMate AI — Migration 007: Notification System (Phase 4, Part 1)
-- Run this in the Supabase SQL Editor before deploying
-- backend/notification_store.py.
--
-- Deliberately separate from the existing `announcements` table (Phase 3),
-- which stays exactly as-is and continues to power the simple post-login
-- banner. This is a richer system: per-user read/unread tracking, and
-- support for BOTH broadcast (everyone) and direct (one specific user)
-- notifications through one schema.
-- ============================================================================

create table if not exists notifications (
    id              uuid primary key default gen_random_uuid(),
    type            text not null check (type in ('broadcast', 'direct')),
    user_id         uuid references users(id) on delete cascade,  -- NULL for broadcast, set for direct
    title           text not null,
    message         text not null,
    is_active       boolean not null default true,   -- admin can retract a broadcast
    created_by      uuid references admin_users(id) on delete set null,
    created_at      timestamptz not null default now(),
    constraint notifications_direct_needs_user check (
        (type = 'broadcast' and user_id is null) or
        (type = 'direct' and user_id is not null)
    )
);
create index if not exists idx_notifications_user_id on notifications (user_id);
create index if not exists idx_notifications_type on notifications (type);
create index if not exists idx_notifications_created_at on notifications (created_at desc);

-- One row per (notification, user) once that user has read it. Absence of
-- a row = unread. Works uniformly for both broadcast (many users, one
-- notification) and direct (one user) notifications.
create table if not exists notification_reads (
    id                  uuid primary key default gen_random_uuid(),
    notification_id     uuid not null references notifications(id) on delete cascade,
    user_id             uuid not null references users(id) on delete cascade,
    read_at             timestamptz not null default now(),
    unique (notification_id, user_id)
);
create index if not exists idx_notification_reads_user_id on notification_reads (user_id);
create index if not exists idx_notification_reads_notification_id on notification_reads (notification_id);

alter table notifications enable row level security;
alter table notification_reads enable row level security;
