"""Add peloton_workouts table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if 'peloton_workouts' not in inspector.get_table_names():
        op.create_table(
            'peloton_workouts',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
            sa.Column('peloton_workout_id', sa.String(64), unique=True, nullable=False),
            sa.Column('ride_title', sa.String(200), nullable=True),
            sa.Column('ride_duration', sa.Integer(), nullable=True),
            sa.Column('total_output', sa.Float(), nullable=True),
            sa.Column('calories', sa.Integer(), nullable=True),
            sa.Column('average_cadence', sa.Float(), nullable=True),
            sa.Column('average_resistance', sa.Float(), nullable=True),
            sa.Column('average_heartrate', sa.Float(), nullable=True),
            sa.Column('leaderboard_rank', sa.Integer(), nullable=True),
            sa.Column('total_leaderboard', sa.Integer(), nullable=True),
            sa.Column('imported_at', sa.DateTime(), nullable=True),
            sa.Column('workout_log_id', sa.Integer(), sa.ForeignKey('workout_logs.id'), nullable=True),
        )


def downgrade():
    op.drop_table('peloton_workouts')
