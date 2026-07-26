-- ============================================================================
-- LearnMate AI — Supabase PostgreSQL schema (Phase 1 of Google Sheets migration)
-- Run this once in the Supabase SQL Editor (Project → SQL Editor → New query).
-- Idempotent: safe to re-run (uses IF NOT EXISTS everywhere).
-- ============================================================================

create extension if not exists pgcrypto;   -- provides gen_random_uuid()

-- ----------------------------------------------------------------------------
-- 1. users  — replaces the "LearnMate AI Users Data" sheet (backend/auth.py)
--    App login stays passwordless (email-only), per current product design.
--    `is_active` powers the User Management "Enable/Disable" feature.
-- ----------------------------------------------------------------------------
create table if not exists users (
    id              uuid primary key default gen_random_uuid(),
    first_name      text not null,
    last_name       text not null,
    email           text not null unique,
    is_active       boolean not null default true,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);
create index if not exists idx_users_email on users (lower(email));
create index if not exists idx_users_created_at on users (created_at desc);

-- ----------------------------------------------------------------------------
-- 2. resume_details — replaces "Users Resume Details" sheet (backend/resume_store.py)
--    One row per saved resume profile per user (matches existing "one active
--    resume, upsert by email" behavior via update_resume()).
-- ----------------------------------------------------------------------------
create table if not exists resume_details (
    id              uuid primary key default gen_random_uuid(),
    user_id         uuid not null references users(id) on delete cascade,
    first_name      text not null,
    last_name       text not null,
    education       text default '',
    skills          text[] default '{}',
    certificates    jsonb default '[]',   -- [{name, issuer, year}]
    internships     jsonb default '[]',   -- [{role, company, duration, description}]
    projects        jsonb default '[]',   -- [{title, description, tech_stack}]
    achievements    text default '',
    hobbies         text[] default '{}',
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);
create index if not exists idx_resume_details_user_id on resume_details (user_id);
create index if not exists idx_resume_details_created_at on resume_details (created_at desc);

-- ----------------------------------------------------------------------------
-- 3. resume_reviews — replaces "Resume Reviews" sheet (backend/resume_review.py)
-- ----------------------------------------------------------------------------
create table if not exists resume_reviews (
    id                  uuid primary key default gen_random_uuid(),
    user_id             uuid not null references users(id) on delete cascade,
    score               integer not null check (score between 0 and 100),
    missing_sections    jsonb default '[]',
    strengths           jsonb default '[]',
    weaknesses          jsonb default '[]',
    suggestions         jsonb default '[]',
    created_at          timestamptz not null default now()
);
create index if not exists idx_resume_reviews_user_id on resume_reviews (user_id);
create index if not exists idx_resume_reviews_created_at on resume_reviews (created_at desc);

-- ----------------------------------------------------------------------------
-- 4. roadmap_requests — replaces "LearnMate AI Users Responses" sheet
--    (backend/responses_store.py). The form submission that triggers generation.
-- ----------------------------------------------------------------------------
create table if not exists roadmap_requests (
    id                      uuid primary key default gen_random_uuid(),
    user_id                 uuid not null references users(id) on delete cascade,
    career_goal             text not null,
    current_level           text not null,
    preferred_domain        text not null,
    learning_preference     text not null,
    study_hours_per_week    integer not null,
    existing_skills         text[] default '{}',
    created_at              timestamptz not null default now()
);
create index if not exists idx_roadmap_requests_user_id on roadmap_requests (user_id);
create index if not exists idx_roadmap_requests_created_at on roadmap_requests (created_at desc);

-- ----------------------------------------------------------------------------
-- 5. roadmaps — NEW capability (per your decision): persists the full
--    AI-generated roadmap output, not just the input request.
-- ----------------------------------------------------------------------------
create table if not exists roadmaps (
    id                  uuid primary key default gen_random_uuid(),
    user_id             uuid not null references users(id) on delete cascade,
    request_id          uuid references roadmap_requests(id) on delete set null,
    title               text default '',
    roadmap_json        jsonb not null,   -- full structured roadmap (weeks/milestones/resources)
    is_offline_fallback boolean not null default false,  -- true if watsonx wasn't configured
    created_at          timestamptz not null default now()
);
create index if not exists idx_roadmaps_user_id on roadmaps (user_id);
create index if not exists idx_roadmaps_created_at on roadmaps (created_at desc);

-- ----------------------------------------------------------------------------
-- 6. ai_responses — NEW: no equivalent existed before (chatbot was
--    session-only). Logs every AI Mentor chatbot exchange.
-- ----------------------------------------------------------------------------
create table if not exists ai_responses (
    id              uuid primary key default gen_random_uuid(),
    user_id         uuid references users(id) on delete set null,  -- null: widget is visible pre-login too
    prompt          text not null,
    response        text not null,
    created_at      timestamptz not null default now()
);
create index if not exists idx_ai_responses_user_id on ai_responses (user_id);
create index if not exists idx_ai_responses_created_at on ai_responses (created_at desc);

-- ----------------------------------------------------------------------------
-- 7. feedback — NEW capability (no existing feedback mechanism in the app).
--    Requires adding a small "Send Feedback" entry point on the user side —
--    flagged for Phase 3 (frontend), not created by this schema alone.
-- ----------------------------------------------------------------------------
create table if not exists feedback (
    id              uuid primary key default gen_random_uuid(),
    user_id         uuid not null references users(id) on delete cascade,
    message         text not null,
    status          text not null default 'open' check (status in ('open', 'resolved')),
    created_at      timestamptz not null default now(),
    resolved_at     timestamptz
);
create index if not exists idx_feedback_user_id on feedback (user_id);
create index if not exists idx_feedback_status on feedback (status);
create index if not exists idx_feedback_created_at on feedback (created_at desc);

-- ----------------------------------------------------------------------------
-- 8. admin_users — separate from `users`. Real bcrypt password hashing here
--    (per your decision), since regular app users stay passwordless.
-- ----------------------------------------------------------------------------
create table if not exists admin_users (
    id                  uuid primary key default gen_random_uuid(),
    email               text not null unique,
    password_hash       text not null,        -- bcrypt hash, generated by backend/admin_auth.py
    first_name          text not null,
    last_name           text not null,
    is_super_admin      boolean not null default false,
    is_active           boolean not null default true,
    created_at          timestamptz not null default now(),
    last_login_at       timestamptz
);
create index if not exists idx_admin_users_email on admin_users (lower(email));

-- ----------------------------------------------------------------------------
-- 9. announcements — admin-authored, shown to users after login.
-- ----------------------------------------------------------------------------
create table if not exists announcements (
    id              uuid primary key default gen_random_uuid(),
    title           text not null,
    body            text not null,
    is_active       boolean not null default true,
    created_by      uuid references admin_users(id) on delete set null,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);
create index if not exists idx_announcements_is_active on announcements (is_active);
create index if not exists idx_announcements_created_at on announcements (created_at desc);

-- ----------------------------------------------------------------------------
-- 10. login_logs — one row per login/logout, for both user types.
--     Streamlit cannot read real client IP/user-agent from a plain script
--     run (no request object) unless deployed behind a proxy that forwards
--     headers — see Phase 2 note in chat for how ip_address/user_agent will
--     be populated honestly (nullable, not faked) where unavailable.
-- ----------------------------------------------------------------------------
create table if not exists login_logs (
    id              uuid primary key default gen_random_uuid(),
    user_id         uuid references users(id) on delete cascade,
    admin_id        uuid references admin_users(id) on delete cascade,
    user_type       text not null check (user_type in ('user', 'admin')),
    login_time      timestamptz not null default now(),
    logout_time     timestamptz,
    ip_address      text,     -- nullable: populated only if the deployment platform exposes it
    user_agent      text,     -- nullable: browser/device string, only if available
    created_at      timestamptz not null default now(),
    constraint login_logs_one_actor check (
        (user_id is not null and admin_id is null) or
        (user_id is null and admin_id is not null)
    )
);
create index if not exists idx_login_logs_user_id on login_logs (user_id);
create index if not exists idx_login_logs_admin_id on login_logs (admin_id);
create index if not exists idx_login_logs_login_time on login_logs (login_time desc);

-- ----------------------------------------------------------------------------
-- 11. user_activity_logs — general activity trail (page views, key actions).
-- ----------------------------------------------------------------------------
create table if not exists user_activity_logs (
    id                  uuid primary key default gen_random_uuid(),
    user_id             uuid references users(id) on delete cascade,
    admin_id            uuid references admin_users(id) on delete cascade,
    activity_type       text not null,      -- e.g. 'page_view', 'resume_generated', 'roadmap_generated'
    activity_detail     jsonb default '{}',
    created_at          timestamptz not null default now(),
    constraint activity_logs_one_actor check (
        (user_id is not null and admin_id is null) or
        (user_id is null and admin_id is not null)
    )
);
create index if not exists idx_activity_logs_user_id on user_activity_logs (user_id);
create index if not exists idx_activity_logs_admin_id on user_activity_logs (admin_id);
create index if not exists idx_activity_logs_created_at on user_activity_logs (created_at desc);

-- ============================================================================
-- Row Level Security
-- All access from the app goes through the SERVICE ROLE key on the backend
-- only (never exposed to the frontend/browser). The service role bypasses
-- RLS by design, so enabling RLS here with no permissive policies simply
-- means: if anyone ever adds the anon/public key to this project, they get
-- zero access by default. Defense in depth, not a functional requirement.
-- ============================================================================
alter table users enable row level security;
alter table resume_details enable row level security;
alter table resume_reviews enable row level security;
alter table roadmap_requests enable row level security;
alter table roadmaps enable row level security;
alter table ai_responses enable row level security;
alter table feedback enable row level security;
alter table admin_users enable row level security;
alter table announcements enable row level security;
alter table login_logs enable row level security;
alter table user_activity_logs enable row level security;

-- ============================================================================
-- End of Phase 1. Do not proceed to Phase 2 (backend code) until you've run
-- this in the Supabase SQL Editor and confirmed all 11 tables were created.
-- ============================================================================
