"""repair missing announcements table drift

Revision ID: 1dff7bf50d72
Revises: 7551ef70cf66
Create Date: 2026-04-15 10:47:10.099393

"""
from typing import Sequence, Union

import sqlmodel
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1dff7bf50d72'
down_revision: Union[str, Sequence[str], None] = '7551ef70cf66'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "announcements" not in inspector.get_table_names():
        op.create_table(
            "announcements",
            sa.Column("title", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
            sa.Column("body", sqlmodel.sql.sqltypes.AutoString(length=5000), nullable=False),
            sa.Column(
                "priority",
                sa.Enum("info", "warning", "critical", name="announcementpriority"),
                nullable=False,
            ),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_pinned", sa.Boolean(), nullable=False),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by", sa.Uuid(), nullable=False),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_announcements_created_by"), "announcements", ["created_by"], unique=False)
        op.create_index(op.f("ix_announcements_id"), "announcements", ["id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    pass
