"""merge heads before shop

Revision ID: f1735bbed1d5
Revises: d1f2a3b4c5d6, 4c208084908b
Create Date: 2026-04-10 00:50:36.510631

"""
from typing import Sequence, Union
import sqlmodel
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1735bbed1d5'
down_revision: Union[str, Sequence[str], None] = ('d1f2a3b4c5d6', '4c208084908b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
