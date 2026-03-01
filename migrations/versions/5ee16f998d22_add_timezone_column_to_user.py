"""Add timezone column to user

Revision ID: 5ee16f998d22
Revises:
Create Date: 2026-03-01

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '5ee16f998d22'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(
            sa.Column('timezone', sa.String(50), nullable=True,
                      server_default='America/New_York')
        )


def downgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('timezone')
