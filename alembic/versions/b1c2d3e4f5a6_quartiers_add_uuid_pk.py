"""quartiers_create_table

Revision ID: b1c2d3e4f5a6
Revises: aef67dfd953f
Create Date: 2026-10-22 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry


revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'aef67dfd953f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'quartiers',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('osm_id', sa.Integer(), nullable=True),
        sa.Column('nom', sa.Text(), nullable=False),
        sa.Column('nom_court', sa.Text(), nullable=False),
        sa.Column('type', sa.Text(), nullable=False),
        sa.Column('actif', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('geom', Geometry('MULTIPOLYGON', srid=4326), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('osm_id'),
    )


def downgrade() -> None:
    op.drop_table('quartiers')
