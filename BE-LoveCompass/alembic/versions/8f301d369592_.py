"""empty message

Revision ID: 8f301d369592
Revises: c4f24380c682
Create Date: 2026-02-14 23:26:23.705960

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f301d369592'
down_revision: Union[str, Sequence[str], None] = 'c4f24380c682'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
