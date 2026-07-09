"""add facebook to product_link_type

Revision ID: 26206aa8b2f7
Revises: 699e45db7938
Create Date: 2026-07-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '26206aa8b2f7'
down_revision: Union[str, Sequence[str], None] = '699e45db7938'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_LINK_TYPES = ("facebook",)


def upgrade() -> None:
    """Upgrade schema."""
    for value in _NEW_LINK_TYPES:
        op.execute(f"ALTER TYPE product_link_type ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    """Downgrade schema."""
    # Note: Postgres does not support removing enum values.
    pass
