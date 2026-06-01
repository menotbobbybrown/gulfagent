-- GulfAgent Phase 4 — RLS verification and missing policies
-- T74: Verify all 7 tables have RLS enabled. Add any missing policies.

-- ─────────────────────────────────────────────
-- 1. Verify RLS is enabled on all tables
-- ─────────────────────────────────────────────
-- Run this check manually in Supabase SQL editor:
-- SELECT tablename, rowsecurity FROM pg_tables
-- WHERE schemaname = 'public'
--   AND tablename IN ('users', 'tasks', 'usage', 'automations', 'skills', 'user_skills', 'approvals');
-- All should show rowsecurity = true.

-- ─────────────────────────────────────────────
-- 2. Ensure RLS is enabled (idempotent)
-- ─────────────────────────────────────────────
ALTER TABLE IF EXISTS public.users       ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.tasks       ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.usage       ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.automations ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.skills      ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.user_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.approvals   ENABLE ROW LEVEL SECURITY;

-- ─────────────────────────────────────────────
-- 3. Recreate all policies idempotently
-- ─────────────────────────────────────────────

-- Users: own row only
DROP POLICY IF EXISTS "users_own" ON public.users;
CREATE POLICY "users_own" ON public.users
    FOR ALL USING (auth.uid() = id);

-- Tasks: own rows only
DROP POLICY IF EXISTS "tasks_own" ON public.tasks;
CREATE POLICY "tasks_own" ON public.tasks
    FOR ALL USING (auth.uid() = user_id);

-- Usage: own rows only
DROP POLICY IF EXISTS "usage_own" ON public.usage;
CREATE POLICY "usage_own" ON public.usage
    FOR ALL USING (auth.uid() = user_id);

-- Automations: own rows only
DROP POLICY IF EXISTS "automations_own" ON public.automations;
CREATE POLICY "automations_own" ON public.automations
    FOR ALL USING (auth.uid() = user_id);

-- Skills: public read (marketplace), admin write
DROP POLICY IF EXISTS "skills_read" ON public.skills;
CREATE POLICY "skills_read" ON public.skills
    FOR SELECT USING (TRUE);

-- UserSkills: own rows only
DROP POLICY IF EXISTS "user_skills_own" ON public.user_skills;
CREATE POLICY "user_skills_own" ON public.user_skills
    FOR ALL USING (auth.uid() = user_id);

-- Approvals: via task ownership (users can only see approvals for their tasks)
DROP POLICY IF EXISTS "approvals_own" ON public.approvals;
CREATE POLICY "approvals_own" ON public.approvals
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.tasks
            WHERE tasks.id = approvals.task_id
              AND tasks.user_id = auth.uid()
        )
    );