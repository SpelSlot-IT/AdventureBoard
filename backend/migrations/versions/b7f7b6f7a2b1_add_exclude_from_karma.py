"""add exclude_from_karma to adventures

Revision ID: b7f7b6f7a2b1
Revises: fix_assignments_top_three
Create Date: 2026-01-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7f7b6f7a2b1"
down_revision = "fix_assignments_top_three"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("adventures", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "exclude_from_karma",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )


def downgrade():
    with op.batch_alter_table("adventures", schema=None) as batch_op:
        batch_op.drop_column("exclude_from_karma")
