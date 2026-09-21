"""Add apple_health_token column to user

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-21

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(
            sa.Column('apple_health_token', sa.String(64), nullable=True)
        )


def downgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('apple_health_token')
