"""admin_fields

Revision ID: b1c2d3e4f5a6
Revises: 055f5fe2a1c0
Create Date: 2026-05-05

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = '055f5fe2a1c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('cars', sa.Column('fuel_consumption', sa.Float(), nullable=False, server_default='8.0'))
    op.add_column('rentals', sa.Column('itinerary_distance_km', sa.Float(), nullable=True))
    op.add_column('rentals', sa.Column('itinerary_start_name', sa.String(255), nullable=True))
    op.add_column('rentals', sa.Column('itinerary_end_name', sa.String(255), nullable=True))
    op.add_column('rentals', sa.Column('itinerary_waypoints', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('cars', 'fuel_consumption')
    op.drop_column('rentals', 'itinerary_distance_km')
    op.drop_column('rentals', 'itinerary_start_name')
    op.drop_column('rentals', 'itinerary_end_name')
    op.drop_column('rentals', 'itinerary_waypoints')
