"""add prix_carburant_estime to location

Revision ID: 88563fdeac78
Revises: d4e5f6a7b8c9
Create Date: 2026-11-01 23:21:02.734189

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '88563fdeac78'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('locations', sa.Column('prix_carburant_estime', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('locations', 'prix_carburant_estime')
