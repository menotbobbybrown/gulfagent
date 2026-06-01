-- GulfAgent Initial Schema
-- Run against Supabase SQL editor or via psql

-- Enable UUID extension (already on in Supabase)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─────────────────────────────────────────────
-- users (mirrors auth.users, public profile)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.users (
    id                    UUID PRIMARY KEY,  -- same as auth.users.id
    email                 TEXT UNIQUE NOT NULL,
    phone                 TEXT,              -- E.164 e.g. +97150...
    full_name             TEXT,
    subscription_tier     TEXT NOT NULL DEFAULT 'basic',   -- basic | pro | enterprise
    subscription_status   TEXT NOT NULL DEFAULT 'trial',   -- trial | active | cancelled
    stripe_customer_id    TEXT,
    stripe_subscription_id TEXT,
    preferred_language    TEXT NOT NULL DEFAULT 'en',      -- en | ar
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ
);

-- auto-create public user on auth signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (id, email, full_name)
    VALUES (NEW.id, NEW.email, NEW.raw_user_meta_data->>'full_name')
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ─────────────────────────────────────────────
-- automations (needed before tasks FK)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.automations (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    prompt        TEXT NOT NULL,
    cron          TEXT NOT NULL,
    active        BOOLEAN NOT NULL DEFAULT TRUE,
    skill_id      UUID,
    last_run      TIMESTAMPTZ,
    next_run      TIMESTAMPTZ,
    bullmq_job_id TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- tasks
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.tasks (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    prompt        TEXT NOT NULL,
    task_type     TEXT NOT NULL DEFAULT 'simple',           -- simple | browser | whatsapp | automation
    status        TEXT NOT NULL DEFAULT 'pending',          -- pending | running | awaiting_approval | completed | failed | cancelled
    result        TEXT,
    error_message TEXT,
    tokens_used   INTEGER NOT NULL DEFAULT 0,
    credits_used  INTEGER NOT NULL DEFAULT 0,
    metadata      JSONB NOT NULL DEFAULT '{}',
    source        TEXT NOT NULL DEFAULT 'dashboard',        -- dashboard | whatsapp | api | automation
    automation_id UUID REFERENCES public.automations(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at    TIMESTAMPTZ,
    completed_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS tasks_user_id_idx ON public.tasks(user_id);
CREATE INDEX IF NOT EXISTS tasks_status_idx ON public.tasks(status);
CREATE INDEX IF NOT EXISTS tasks_created_at_idx ON public.tasks(created_at DESC);

-- ─────────────────────────────────────────────
-- usage  (monthly credit tracking)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.usage (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    year_month    TEXT NOT NULL,                -- "2024-01"
    credits_used  INTEGER NOT NULL DEFAULT 0,
    tasks_run     INTEGER NOT NULL DEFAULT 0,
    credits_limit INTEGER NOT NULL DEFAULT 5000,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, year_month)
);

-- ─────────────────────────────────────────────
-- skills + user_skills
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.skills (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    slug            TEXT UNIQUE NOT NULL,
    description     TEXT,
    category        TEXT NOT NULL,  -- Research | E-commerce | Government | Finance | HR
    prompt_template TEXT NOT NULL,
    icon            TEXT,
    default_cron    TEXT,
    credit_cost     INTEGER NOT NULL DEFAULT 10,
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.user_skills (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    skill_id     UUID NOT NULL REFERENCES public.skills(id) ON DELETE CASCADE,
    activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, skill_id)
);

-- ─────────────────────────────────────────────
-- approvals
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.approvals (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id        UUID NOT NULL REFERENCES public.tasks(id) ON DELETE CASCADE,
    action_type    TEXT NOT NULL,     -- email | form_submit | payment | file_delete
    action_payload JSONB NOT NULL DEFAULT '{}',
    decision       TEXT,              -- approved | denied | timeout
    expires_at     TIMESTAMPTZ NOT NULL,
    decided_at     TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- Row-Level Security
-- ─────────────────────────────────────────────
ALTER TABLE public.users        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tasks        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.automations  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_skills  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.approvals    ENABLE ROW LEVEL SECURITY;

-- users: own row only
CREATE POLICY "users_own" ON public.users
    FOR ALL USING (auth.uid() = id);

-- tasks: own rows only
CREATE POLICY "tasks_own" ON public.tasks
    FOR ALL USING (auth.uid() = user_id);

-- usage: own rows only
CREATE POLICY "usage_own" ON public.usage
    FOR ALL USING (auth.uid() = user_id);

-- automations: own rows only
CREATE POLICY "automations_own" ON public.automations
    FOR ALL USING (auth.uid() = user_id);

-- skills: public read
CREATE POLICY "skills_read" ON public.skills
    FOR SELECT USING (TRUE);

-- user_skills: own rows
CREATE POLICY "user_skills_own" ON public.user_skills
    FOR ALL USING (auth.uid() = user_id);

-- approvals: via task ownership
CREATE POLICY "approvals_own" ON public.approvals
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.tasks
            WHERE tasks.id = approvals.task_id
              AND tasks.user_id = auth.uid()
        )
    );
