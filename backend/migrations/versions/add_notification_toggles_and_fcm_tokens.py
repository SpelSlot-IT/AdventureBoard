"""add user notification toggles and fcm_tokens table

Revision ID: add_notif_fcm
Revises: add_is_story_adventure
Create Date: 2026-02-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_notif_fcm"
down_revision = "add_is_story_adventure"
branch_labels = None
depends_on = None


def upgrade():
    # Create fcm_tokens table if it does not exist
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("fcm_tokens"):
        op.create_table(
            "fcm_tokens",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("token", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token", name="uq_fcm_tokens_token"),
        )

    # Add notification toggle columns to users
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("notify_new_adventure", sa.Boolean(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("notify_deadline", sa.Boolean(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("notify_assignments", sa.Boolean(), nullable=True)
        )


def downgrade():
    # Remove notification toggles from users
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("notify_assignments")
        batch_op.drop_column("notify_deadline")
        batch_op.drop_column("notify_new_adventure")

    # Drop fcm_tokens table
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("fcm_tokens"):
        op.drop_table("fcm_tokens")
