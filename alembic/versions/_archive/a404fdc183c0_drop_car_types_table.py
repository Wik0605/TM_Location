"""drop_car_types_table

Revision ID: a404fdc183c0
Revises: 6294cbc48afc
Create Date: 2026-05-02 12:21:41.043052

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a404fdc183c0'
down_revision: Union[str, Sequence[str], None] = '6294cbc48afc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('car_types')


def downgrade() -> None:
    op.create_table(
        'car_types',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
