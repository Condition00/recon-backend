"""add zones catalog and zone registrations

Revision ID: a1b2c3d4e5f6
Revises: f7a8c9d0e1f2
Create Date: 2026-04-16 16:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f7a8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "zones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("short_name", sa.String(length=40), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False),
        sa.Column("zone_type", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="green"),
        sa.Column("location", sa.String(length=200), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("color", sa.String(length=40), nullable=False, server_default="#0EA5E9"),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("short_name", name="uq_zones_short_name"),
    )
    op.create_index("ix_zones_name", "zones", ["name"], unique=False)
    op.create_index("ix_zones_short_name", "zones", ["short_name"], unique=False)
    op.create_index("ix_zones_category", "zones", ["category"], unique=False)
    op.create_index("ix_zones_zone_type", "zones", ["zone_type"], unique=False)
    op.create_index("ix_zones_is_active", "zones", ["is_active"], unique=False)

    op.create_table(
        "zone_registrations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("zone_id", sa.Uuid(), nullable=False),
        sa.Column("pass_code", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checked_in_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["checked_in_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"]),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("participant_id", "zone_id", name="uq_zone_registrations_participant_zone"),
        sa.UniqueConstraint("pass_code", name="uq_zone_registrations_pass_code"),
    )
    op.create_index("ix_zone_registrations_participant_id", "zone_registrations", ["participant_id"], unique=False)
    op.create_index("ix_zone_registrations_zone_id", "zone_registrations", ["zone_id"], unique=False)
    op.create_index("ix_zone_registrations_pass_code", "zone_registrations", ["pass_code"], unique=False)
    op.create_index("ix_zone_registrations_is_active", "zone_registrations", ["is_active"], unique=False)
    op.create_index(
        "ix_zone_registrations_participant_active",
        "zone_registrations",
        ["participant_id", "is_active"],
        unique=False,
    )
    op.create_index(
        "ix_zone_registrations_zone_active",
        "zone_registrations",
        ["zone_id", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_zone_registrations_zone_active", table_name="zone_registrations")
    op.drop_index("ix_zone_registrations_participant_active", table_name="zone_registrations")
    op.drop_index("ix_zone_registrations_is_active", table_name="zone_registrations")
    op.drop_index("ix_zone_registrations_pass_code", table_name="zone_registrations")
    op.drop_index("ix_zone_registrations_zone_id", table_name="zone_registrations")
    op.drop_index("ix_zone_registrations_participant_id", table_name="zone_registrations")
    op.drop_table("zone_registrations")

    op.drop_index("ix_zones_is_active", table_name="zones")
    op.drop_index("ix_zones_zone_type", table_name="zones")
    op.drop_index("ix_zones_category", table_name="zones")
    op.drop_index("ix_zones_short_name", table_name="zones")
    op.drop_index("ix_zones_name", table_name="zones")
    op.drop_table("zones")
