"""merge heads zone_routiere

Revision ID: 2db752798e31
Revises: 8b70a50dba4b, e5f6a7b8c9d0
Create Date: 2026-11-12 11:13:18.183723

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2db752798e31'
down_revision: Union[str, Sequence[str], None] = ('8b70a50dba4b', 'e5f6a7b8c9d0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
