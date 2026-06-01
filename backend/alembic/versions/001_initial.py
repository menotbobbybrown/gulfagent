"""
GulfAgent — Initial database schema.

Creates all Phase 1 tables: users, tasks, usage, automations, skills,
user_skills, approvals, plus triggers and RLS policies.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgcrypto (idempotent)
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # ── users ──────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("email", sa.Text, unique=True, nullable=False),
        sa.Column("phone", sa.Text, nullable=True),
        sa.Column("full_name", sa.Text, nullable=True),
        sa.Column("subscription_tier", sa.Text, nullable=False, server_default="basic"),
        sa.Column("subscription_status", sa.Text, nullable=False, server_default="trial"),
        sa.Column("stripe_customer_id", sa.Text, nullable=True),
        sa.Column("stripe_subscription_id", sa.Text, nullable=True),
        sa.Column("preferred_language", sa.Text, nullable=False, server_default="en"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.execute("ALTER TABLE public.users ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY users_own ON public.users FOR ALL USING (auth.uid() = id)"
    )

    # ── automations ────────────────────────────
    op.create_table(
        "automations",
        sa.Column("id", UUID, primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("cron", sa.Text, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("skill_id", UUID, nullable=True),
        sa.Column("last_run", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run", sa.DateTime(timezone=True), nullable=True),
        sa.Column("bullmq_job_id", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("ALTER TABLE public.automations ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY automations_own ON public.automations FOR ALL USING (auth.uid() = user_id)"
    )

    # ── tasks ──────────────────────────────────
    op.create_table(
        "tasks",
        sa.Column("id", UUID, primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("task_type", sa.Text, nullable=False, server_default="simple"),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column("result", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("tokens_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("credits_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("source", sa.Text, nullable=False, server_default="dashboard"),
        sa.Column("automation_id", UUID, sa.ForeignKey("automations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("tasks_user_id_idx", "tasks", ["user_id"])
    op.create_index("tasks_status_idx", "tasks", ["status"])
    op.create_index("tasks_created_at_idx", "tasks", [sa.text("created_at DESC")])
    op.execute("ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tasks_own ON public.tasks FOR ALL USING (auth.uid() = user_id)"
    )

    # ── usage ──────────────────────────────────
    op.create_table(
        "usage",
        sa.Column("id", UUID, primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("year_month", sa.Text, nullable=False),
        sa.Column("credits_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tasks_run", sa.Integer, nullable=False, server_default="0"),
        sa.Column("credits_limit", sa.Integer, nullable=False, server_default="5000"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("user_id", "year_month"),
    )
    op.execute("ALTER TABLE public.usage ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY usage_own ON public.usage FOR ALL USING (auth.uid() = user_id)"
    )

    # ── skills ─────────────────────────────────
    op.create_table(
        "skills",
        sa.Column("id", UUID, primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("slug", sa.Text, unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.Text, nullable=False),
        sa.Column("prompt_template", sa.Text, nullable=False),
        sa.Column("icon", sa.Text, nullable=True),
        sa.Column("default_cron", sa.Text, nullable=True),
        sa.Column("credit_cost", sa.Integer, nullable=False, server_default="10"),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("ALTER TABLE public.skills ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY skills_read ON public.skills FOR SELECT USING (TRUE)"
    )

    # ── user_skills ────────────────────────────
    op.create_table(
        "user_skills",
        sa.Column("id", UUID, primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", UUID, sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "skill_id"),
    )
    op.execute("ALTER TABLE public.user_skills ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY user_skills_own ON public.user_skills FOR ALL USING (auth.uid() = user_id)"
    )

    # ── approvals ──────────────────────────────
    op.create_table(
        "approvals",
        sa.Column("id", UUID, primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column("task_id", UUID, sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action_type", sa.Text, nullable=False),
        sa.Column("action_payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("decision", sa.Text, nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("ALTER TABLE public.approvals ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY approvals_own ON public.approvals FOR ALL USING ("
        "  EXISTS ("
        "    SELECT 1 FROM public.tasks"
        "    WHERE tasks.id = approvals.task_id"
        "      AND tasks.user_id = auth.uid()"
        "  )"
        ")"
    )

    # ── auto-create user trigger ───────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION public.handle_new_user()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO public.users (id, email, full_name)
            VALUES (NEW.id, NEW.email, NEW.raw_user_meta_data->>'full_name')
            ON CONFLICT (id) DO NOTHING;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users
    """)
    op.execute("""
        CREATE TRIGGER on_auth_user_created
            AFTER INSERT ON auth.users
            FOR EACH ROW EXECUTE FUNCTION public.handle_new_user()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users")
    op.execute("DROP FUNCTION IF EXISTS public.handle_new_user()")
    op.drop_table("approvals")
    op.drop_table("user_skills")
    op.drop_table("skills")
    op.drop_table("usage")
    op.drop_table("tasks")
    op.drop_table("automations")
    op.drop_table("users")