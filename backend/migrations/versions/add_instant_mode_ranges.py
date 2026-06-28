"""add instant_mode_ranges table

Revision ID: add_instant_mode_ranges
Revises: add_is_story_adventure
Create Date: 2026-06-28 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "add_instant_mode_ranges"
down_revision = "add_is_story_adventure"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "instant_mode_ranges",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_recurring", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("recurrence_weekday", sa.Integer(), nullable=True),
        sa.Column("recurrence_week_of_month", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("instant_mode_ranges")
