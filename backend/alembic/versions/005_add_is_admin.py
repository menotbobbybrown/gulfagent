"""add is_admin column to users"""
from alembic import op
import sqlalchemy as sa
revision = '005'
down_revision = '004'
def upgrade():
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), server_default='false', nullable=False))
def downgrade():
    op.drop_column('users', 'is_admin')
