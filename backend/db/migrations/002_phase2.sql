-- GulfAgent Phase 2 additions
-- Run after 001_initial.sql

-- users: phone column already in schema, ensure index for fast lookup
CREATE INDEX IF NOT EXISTS users_phone_idx ON public.users(phone)
    WHERE phone IS NOT NULL;

-- tasks: index on source for WhatsApp filtering
CREATE INDEX IF NOT EXISTS tasks_source_idx ON public.tasks(source);

-- approvals: index on task_id + decision for fast pending lookups
CREATE INDEX IF NOT EXISTS approvals_task_id_idx ON public.approvals(task_id);
CREATE INDEX IF NOT EXISTS approvals_pending_idx ON public.approvals(decision)
    WHERE decision IS NULL;

-- Supabase Storage bucket for browser screenshots
-- Run via Supabase dashboard or CLI:
-- supabase storage create gulfagent-screenshots --public
-- (Public read so dashboard img src works without signed URLs)
