"""Phase 2: users index, approvals indexes, storage bucket note"""
from alembic import op
revision = '002_phase2'
down_revision = '001_initial'
def upgrade():
    op.execute("CREATE INDEX IF NOT EXISTS users_phone_idx ON public.users(phone) WHERE phone IS NOT NULL;")
    op.execute("CREATE INDEX IF NOT EXISTS tasks_source_idx ON public.tasks(source);")
    op.execute("CREATE INDEX IF NOT EXISTS approvals_task_id_idx ON public.approvals(task_id);")
    op.execute("CREATE INDEX IF NOT EXISTS approvals_pending_idx ON public.approvals(decision) WHERE decision IS NULL;")
def downgrade():
    op.execute("DROP INDEX IF EXISTS approvals_pending_idx;")
    op.execute("DROP INDEX IF EXISTS approvals_task_id_idx;")
    op.execute("DROP INDEX IF EXISTS tasks_source_idx;")
    op.execute("DROP INDEX IF EXISTS users_phone_idx;")