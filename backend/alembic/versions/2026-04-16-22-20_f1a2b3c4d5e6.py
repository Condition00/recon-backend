"""drop legacy points outbox table

Revision ID: f1a2b3c4d5e6
Revises: e6f7a8b9c0d1
Create Date: 2026-04-16 22:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if _table_exists("points_outbox"):
        op.drop_table("points_outbox")


def downgrade() -> None:
    if not _table_exists("points_outbox"):
        op.create_table(
            "points_outbox",
            sa.Column("event_type", sa.String(length=64), nullable=False),
            sa.Column("participant_id", sa.Uuid(), nullable=False),
            sa.Column("delta", sa.Integer(), nullable=False),
            sa.Column("resulting_balance", sa.Integer(), nullable=False),
            sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_error", sa.String(length=1000), nullable=True),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("TIMEZONE('utc', NOW())"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("TIMEZONE('utc', NOW())"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["participant_id"], ["participants.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_points_outbox_participant_id"), "points_outbox", ["participant_id"])
