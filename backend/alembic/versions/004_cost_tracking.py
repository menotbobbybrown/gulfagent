"""Phase 4: Add cost tracking columns to tasks table"""
from alembic import op
import sqlalchemy as sa
revision = '004_cost_tracking'
down_revision = '003_phase4_rls'
def upgrade():
    op.add_column('tasks', sa.Column('model_used', sa.Text(), nullable=True))
    op.add_column('tasks', sa.Column('cost_usd', sa.Numeric(12,6), server_default='0', nullable=False))
    op.add_column('tasks', sa.Column('latency_ms', sa.Integer(), server_default='0', nullable=False))
    op.add_column('tasks', sa.Column('fallback_used', sa.Boolean(), server_default='false', nullable=False))
def downgrade():
    op.drop_column('tasks', 'fallback_used')
    op.drop_column('tasks', 'latency_ms')
    op.drop_column('tasks', 'cost_usd')
    op.drop_column('tasks', 'model_used')