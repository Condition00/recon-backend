"""add form_response to users

Revision ID: 4bda72c9a195
Revises: b49571b8bc83
Create Date: 2026-03-30 16:01:51.710980

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '4bda72c9a195'
down_revision: Union[str, Sequence[str], None] = 'b49571b8bc83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('form_response', JSONB, nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'form_response')
