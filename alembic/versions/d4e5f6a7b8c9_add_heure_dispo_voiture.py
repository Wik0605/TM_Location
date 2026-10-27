"""add heure_dispo_debut and heure_dispo_fin to voitures

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-10-27

"""
from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a7b8c9"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("voitures", sa.Column("heure_dispo_debut", sa.Time(), nullable=True))
    op.add_column("voitures", sa.Column("heure_dispo_fin", sa.Time(), nullable=True))


def downgrade() -> None:
    op.drop_column("voitures", "heure_dispo_fin")
    op.drop_column("voitures", "heure_dispo_debut")
