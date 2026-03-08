"""Add micro_fast table and default_micro_fast_minutes to user

Revision ID: a1b2c3d4e5f6
Revises: 5ee16f998d22
Create Date: 2026-03-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = 'a1b2c3d4e5f6'
down_revision = '5ee16f998d22'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # Add default_micro_fast_minutes to user table (skip if column already exists)
    existing_user_cols = {c['name'] for c in inspector.get_columns('user')}
    if 'default_micro_fast_minutes' not in existing_user_cols:
        with op.batch_alter_table('user') as batch_op:
            batch_op.add_column(
                sa.Column('default_micro_fast_minutes', sa.Integer(), nullable=True,
                          server_default='180')
            )

    # Create micro_fast table only if it doesn't already exist
    if 'micro_fast' not in inspector.get_table_names():
        op.create_table(
            'micro_fast',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
            sa.Column('started_at', sa.DateTime(), nullable=False),
            sa.Column('ended_at', sa.DateTime(), nullable=True),
            sa.Column('target_minutes', sa.Integer(), nullable=False, server_default='180'),
            sa.Column('completed', sa.Boolean(), nullable=True, server_default='0'),
            sa.Column('label', sa.String(50), nullable=True),
            sa.Column('note', sa.String(200), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )


def downgrade():
    op.drop_table('micro_fast')
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('default_micro_fast_minutes')
