"""add telegram, medium, tiktok to product_link_type

Revision ID: 671a2baf0ba3
Revises: f23a9f965d21
Create Date: 2026-07-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '671a2baf0ba3'
down_revision: Union[str, Sequence[str], None] = 'f23a9f965d21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_LINK_TYPES = ("telegram", "medium", "tiktok")


def upgrade() -> None:
    """Upgrade schema."""
    for value in _NEW_LINK_TYPES:
        op.execute(f"ALTER TYPE product_link_type ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    """Downgrade schema."""
    # Note: Postgres does not support removing enum values.
    pass
