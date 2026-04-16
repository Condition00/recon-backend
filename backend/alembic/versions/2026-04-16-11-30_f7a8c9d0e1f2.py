"""points durability + projection hardening

Revision ID: f7a8c9d0e1f2
Revises: b3c9d7e6f2aa
Create Date: 2026-04-16 11:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f7a8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "b3c9d7e6f2aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE point_ledger
        SET idempotency_key = 'legacy-' || id::text
        WHERE idempotency_key IS NULL
        """
    )
    op.alter_column("point_ledger", "idempotency_key", nullable=False)

    op.create_table(
        "participant_points",
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("total_points", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "last_activity_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"]),
        sa.PrimaryKeyConstraint("participant_id"),
    )
    op.create_index(
        "ix_participant_points_rank_order",
        "participant_points",
        ["total_points", "last_activity_at", "participant_id"],
        unique=False,
        postgresql_using="btree",
    )

    op.execute(
        """
        INSERT INTO participant_points (participant_id, total_points, last_activity_at)
        SELECT
            participant_id,
            SUM(amount) AS total_points,
            MAX(created_at) AS last_activity_at
        FROM point_ledger
        GROUP BY participant_id
        ON CONFLICT (participant_id) DO UPDATE
        SET total_points = EXCLUDED.total_points,
            last_activity_at = EXCLUDED.last_activity_at
        """
    )

    op.create_table(
        "points_outbox",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("resulting_balance", sa.Integer(), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=1000), nullable=True),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_points_outbox_id"), "points_outbox", ["id"], unique=False)
    op.create_index(
        op.f("ix_points_outbox_participant_id"),
        "points_outbox",
        ["participant_id"],
        unique=False,
    )
    op.create_index(
        "ix_points_outbox_ready",
        "points_outbox",
        ["next_attempt_at", "created_at"],
        unique=False,
        postgresql_where=sa.text("sent_at IS NULL"),
    )

    op.create_index(
        "ix_point_ledger_created_at_id",
        "point_ledger",
        ["created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_point_ledger_participant_created_at_id",
        "point_ledger",
        ["participant_id", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_point_ledger_reason_created_at_id",
        "point_ledger",
        ["reason", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_point_ledger_reason_created_at_id", table_name="point_ledger")
    op.drop_index("ix_point_ledger_participant_created_at_id", table_name="point_ledger")
    op.drop_index("ix_point_ledger_created_at_id", table_name="point_ledger")

    op.drop_index("ix_points_outbox_ready", table_name="points_outbox")
    op.drop_index(op.f("ix_points_outbox_participant_id"), table_name="points_outbox")
    op.drop_index(op.f("ix_points_outbox_id"), table_name="points_outbox")
    op.drop_table("points_outbox")

    op.drop_index("ix_participant_points_rank_order", table_name="participant_points")
    op.drop_table("participant_points")

    op.alter_column("point_ledger", "idempotency_key", nullable=True)
