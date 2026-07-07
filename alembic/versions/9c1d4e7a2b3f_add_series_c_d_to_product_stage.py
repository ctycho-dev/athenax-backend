"""add series c, series d to product_stage

Revision ID: 9c1d4e7a2b3f
Revises: 2b28587893ca
Create Date: 2026-07-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '9c1d4e7a2b3f'
down_revision: Union[str, Sequence[str], None] = '2b28587893ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_STAGES = ("Series C", "Series D")


def upgrade() -> None:
    """Upgrade schema."""
    for value in _NEW_STAGES:
        op.execute(f"ALTER TYPE product_stage ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    """Downgrade schema."""
    # Note: Postgres does not support removing enum values.
    pass
