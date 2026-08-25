"""add itineraire_source to locations

Revision ID: 799b33d1e864
Revises: ce7013874243
Create Date: 2026-08-25 20:50:35.732151

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '799b33d1e864'
down_revision: Union[str, Sequence[str], None] = 'ce7013874243'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'locations',
        sa.Column('itineraire_source', sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('locations', 'itineraire_source')
