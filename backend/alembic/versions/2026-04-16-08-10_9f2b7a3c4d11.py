"""add point ledger table

Revision ID: 9f2b7a3c4d11
Revises: 1734fadc119b
Create Date: 2026-04-16 08:10:00.000000

"""

from typing import Sequence, Union

import sqlmodel
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f2b7a3c4d11"
down_revision: Union[str, Sequence[str], None] = ("1734fadc119b", "4c208084908b")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "point_ledger",
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reason", sqlmodel.sql.sqltypes.AutoString(length=120), nullable=False),
        sa.Column("reference_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(length=300), nullable=True),
        sa.Column("resulting_balance", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("awarded_by_user_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("amount <> 0", name="ck_point_ledger_amount_nonzero"),
        sa.ForeignKeyConstraint(["awarded_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_point_ledger_id"), "point_ledger", ["id"], unique=False)
    op.create_index(op.f("ix_point_ledger_participant_id"), "point_ledger", ["participant_id"], unique=False)
    op.create_index(op.f("ix_point_ledger_reason"), "point_ledger", ["reason"], unique=False)
    op.create_index(op.f("ix_point_ledger_reference_id"), "point_ledger", ["reference_id"], unique=False)
    op.create_index(op.f("ix_point_ledger_awarded_by_user_id"), "point_ledger", ["awarded_by_user_id"], unique=False)
    op.create_index(op.f("ix_point_ledger_idempotency_key"), "point_ledger", ["idempotency_key"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_point_ledger_idempotency_key"), table_name="point_ledger")
    op.drop_index(op.f("ix_point_ledger_awarded_by_user_id"), table_name="point_ledger")
    op.drop_index(op.f("ix_point_ledger_reference_id"), table_name="point_ledger")
    op.drop_index(op.f("ix_point_ledger_reason"), table_name="point_ledger")
    op.drop_index(op.f("ix_point_ledger_participant_id"), table_name="point_ledger")
    op.drop_index(op.f("ix_point_ledger_id"), table_name="point_ledger")
    op.drop_table("point_ledger")
