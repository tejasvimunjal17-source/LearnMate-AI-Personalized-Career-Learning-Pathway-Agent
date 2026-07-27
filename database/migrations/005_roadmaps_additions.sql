-- ============================================================================
-- LearnMate AI — Migration 005: roadmaps additions for Phase 4
-- Run this in the Supabase SQL Editor before deploying
-- backend/roadmap_store.py.
--
-- roadmaps.roadmap_json (from Phase 1) already holds the complete AI
-- output. These columns denormalize the specific fields requested for
-- Phase 4 (career goal, current skills, certifications, projects,
-- estimated timeline, weekly roadmap) so they're directly queryable/
-- filterable without unpacking JSON - roadmap_json remains the full
-- source of truth.
-- ============================================================================

alter table roadmaps add column if not exists career_goal text default '';
alter table roadmaps add column if not exists current_skills text[] default '{}';
alter table roadmaps add column if not exists weekly_roadmap jsonb default '[]';
alter table roadmaps add column if not exists certifications text[] default '{}';
alter table roadmaps add column if not exists projects text[] default '{}';
alter table roadmaps add column if not exists estimated_timeline text default '';
