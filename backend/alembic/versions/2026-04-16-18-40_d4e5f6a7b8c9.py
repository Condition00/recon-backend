"""enforce zones status values with check constraint

Revision ID: d4e5f6a7b8c9
Revises: c9d8e7f6a5b4
Create Date: 2026-04-16 18:40:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c9d8e7f6a5b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE zones DROP CONSTRAINT IF EXISTS ck_zones_status_valid")
    op.create_check_constraint(
        "ck_zones_status_valid",
        "zones",
        "status IN ('green', 'amber', 'red', 'closed')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_zones_status_valid", "zones", type_="check")

