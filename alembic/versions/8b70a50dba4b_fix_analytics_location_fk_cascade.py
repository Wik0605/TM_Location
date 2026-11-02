"""fix_analytics_location_fk_cascade

Revision ID: 8b70a50dba4b
Revises: 88563fdeac78
Create Date: 2026-11-02 22:26:31.298540

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b70a50dba4b'
down_revision: Union[str, Sequence[str], None] = '88563fdeac78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("analytics_events_location_id_fkey", "analytics_events", type_="foreignkey")
    op.create_foreign_key(
        "analytics_events_location_id_fkey",
        "analytics_events", "locations",
        ["location_id"], ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("analytics_events_location_id_fkey", "analytics_events", type_="foreignkey")
    op.create_foreign_key(
        "analytics_events_location_id_fkey",
        "analytics_events", "locations",
        ["location_id"], ["id"],
    )
