"""enable postgis

Revision ID: c3d4e5f6a7b8
Revises:
Create Date: 2026-10-25

"""
from alembic import op


revision = 'c3d4e5f6a7b8'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')


def downgrade() -> None:
    pass
