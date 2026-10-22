"""quartiers_add_uuid_pk

Revision ID: b1c2d3e4f5a6
Revises: aef67dfd953f
Create Date: 2026-10-22 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'aef67dfd953f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.add_column('quartiers', sa.Column(
        'id',
        sa.UUID(),
        nullable=False,
        server_default=sa.text('uuid_generate_v4()'),
    ))
    op.create_primary_key('quartiers_pkey', 'quartiers', ['id'])


def downgrade() -> None:
    op.drop_constraint('quartiers_pkey', 'quartiers', type_='primary')
    op.drop_column('quartiers', 'id')
