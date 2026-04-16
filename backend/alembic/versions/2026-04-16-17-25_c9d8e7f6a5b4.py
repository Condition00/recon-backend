"""merge alembic heads after zones portal work

Revision ID: c9d8e7f6a5b4
Revises: 346ed7d41b62, 1dff7bf50d72, a1b2c3d4e5f6
Create Date: 2026-04-16 17:25:00.000000

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "c9d8e7f6a5b4"
down_revision: Union[str, Sequence[str], None] = (
    "346ed7d41b62",
    "1dff7bf50d72",
    "a1b2c3d4e5f6",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
