"""merge heads

Revision ID: 2dcde77a25a2
Revises: d1f2a3b4c5d6, 4c208084908b, 1734fadc119b
Create Date: 2026-04-10 01:28:57.598695

"""
from typing import Sequence, Union
import sqlmodel
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2dcde77a25a2'
down_revision: Union[str, Sequence[str], None] = ('d1f2a3b4c5d6', '4c208084908b', '1734fadc119b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
