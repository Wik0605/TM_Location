"""add slug to voitures

Revision ID: a1b2c3d4e5f6
Revises: d5dd362f212f
Create Date: 2026-09-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.utils.slug import slugify


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'd5dd362f212f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _unique_slug_sync(bind, base: str, taken: set[str]) -> str:
    candidate = base
    suffix = 2
    while candidate in taken:
        candidate = f"{base}-{suffix}"
        suffix += 1
    taken.add(candidate)
    return candidate


def upgrade() -> None:
    with op.batch_alter_table('voitures') as batch:
        batch.add_column(sa.Column('slug', sa.String(length=140), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, nom FROM voitures")).fetchall()
    taken: set[str] = set()
    for row in rows:
        base = slugify(row.nom)
        slug = _unique_slug_sync(bind, base, taken)
        bind.execute(
            sa.text("UPDATE voitures SET slug = :slug WHERE id = :id"),
            {"slug": slug, "id": row.id},
        )

    with op.batch_alter_table('voitures') as batch:
        batch.alter_column('slug', existing_type=sa.String(length=140), nullable=False)
        batch.create_unique_constraint('uq_voitures_slug', ['slug'])
        batch.create_index('ix_voitures_slug', ['slug'])


def downgrade() -> None:
    with op.batch_alter_table('voitures') as batch:
        batch.drop_index('ix_voitures_slug')
        batch.drop_constraint('uq_voitures_slug', type_='unique')
        batch.drop_column('slug')
