"""add zone_routiere to voitures

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-11-12

"""
from alembic import op
import sqlalchemy as sa

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "voitures",
        sa.Column(
            "zone_routiere",
            sa.String(length=10),
            nullable=False,
            server_default="zone3",
        ),
    )
    op.create_index(
        "ix_voitures_zone_routiere", "voitures", ["zone_routiere"]
    )


def downgrade() -> None:
    op.drop_index("ix_voitures_zone_routiere", table_name="voitures")
    op.drop_column("voitures", "zone_routiere")
