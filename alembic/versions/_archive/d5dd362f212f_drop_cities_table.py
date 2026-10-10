"""drop cities table

Revision ID: d5dd362f212f
Revises: 8aecf69bb79a
Create Date: 2026-09-13 17:22:45.149855

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5dd362f212f'
down_revision: Union[str, Sequence[str], None] = '8aecf69bb79a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('cities')


def downgrade() -> None:
    op.create_table(
        'cities',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False, unique=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
    )
