"""add description to voitures

Revision ID: 7ef94582e88c
Revises: a75a46871ff0
Create Date: 2026-07-16 13:42:54.981029

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ef94582e88c'
down_revision: Union[str, Sequence[str], None] = 'a75a46871ff0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('voitures', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('description', sa.Text(), nullable=False, server_default='')
        )
    with op.batch_alter_table('voitures', schema=None) as batch_op:
        batch_op.alter_column('description', server_default=None)


def downgrade() -> None:
    with op.batch_alter_table('voitures', schema=None) as batch_op:
        batch_op.drop_column('description')
