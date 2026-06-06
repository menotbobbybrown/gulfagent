"""add is_admin column to users"""
from alembic import op
import sqlalchemy as sa
revision = '005_add_is_admin'
down_revision = '004_cost_tracking'
def upgrade():
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), server_default='false', nullable=False))
def downgrade():
    op.drop_column('users', 'is_admin')
