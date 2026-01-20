"""ensure assignments schema matches current model

Revision ID: fix_assignments_top_three
Revises: a1601ab07798, add_requested_players
Create Date: 2026-01-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "fix_assignments_top_three"
down_revision = ("a1601ab07798", "add_requested_players")
branch_labels = None
depends_on = None


def _column_exists(bind, table_name, column_name):
    inspector = sa.inspect(bind)
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade():
    bind = op.get_bind()
    has_top_three = _column_exists(bind, "assignments", "top_three")
    has_preference_place = _column_exists(bind, "assignments", "preference_place")

    if has_top_three or not has_preference_place:
        with op.batch_alter_table("assignments", schema=None) as batch_op:
            if has_top_three:
                batch_op.drop_column("top_three")
            if not has_preference_place:
                batch_op.add_column(sa.Column("preference_place", sa.Integer(), nullable=True))


def downgrade():
    bind = op.get_bind()
    has_top_three = _column_exists(bind, "assignments", "top_three")
    has_preference_place = _column_exists(bind, "assignments", "preference_place")

    if not has_top_three or has_preference_place:
        with op.batch_alter_table("assignments", schema=None) as batch_op:
            if not has_top_three:
                batch_op.add_column(
                    sa.Column(
                        "top_three",
                        sa.Boolean(),
                        nullable=False,
                        server_default=sa.text("0"),
                    )
                )
            if has_preference_place:
                batch_op.drop_column("preference_place")
