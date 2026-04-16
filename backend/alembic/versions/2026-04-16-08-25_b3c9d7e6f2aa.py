"""merge parallel heads for points domain

Revision ID: b3c9d7e6f2aa
Revises: d1f2a3b4c5d6, 4c208084908b, 9f2b7a3c4d11
Create Date: 2026-04-16 08:25:00.000000

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "b3c9d7e6f2aa"
down_revision: Union[str, Sequence[str], None] = (
    "d1f2a3b4c5d6",
    "9f2b7a3c4d11",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
