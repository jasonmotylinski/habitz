"""Drop unused api_key table (dead external recipe API + key system)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-23

The external recipe API (meal_planner/api.py) and its API-key management
UI were removed: zero keys ever issued, zero nginx hits. Drop the table.
"""
from alembic import op
import sqlalchemy as sa

revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table('api_key')


def downgrade():
    op.create_table(
        'api_key',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('key', sa.String(64), nullable=False),
        sa.Column('name', sa.String(255)),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('last_used', sa.DateTime()),
        sa.Column('is_active', sa.Boolean()),
    )
    with op.batch_alter_table('api_key') as batch_op:
        batch_op.create_unique_constraint('uq_api_key_key', ['key'])
        batch_op.create_index('ix_api_key_key', ['key'])
