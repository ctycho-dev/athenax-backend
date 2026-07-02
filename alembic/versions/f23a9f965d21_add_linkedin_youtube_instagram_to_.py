"""add linkedin, youtube, instagram to product_link_type

Revision ID: f23a9f965d21
Revises: 445db6e4fe53
Create Date: 2026-07-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f23a9f965d21'
down_revision: Union[str, Sequence[str], None] = '445db6e4fe53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_LINK_TYPES = ("linkedin", "youtube", "instagram")


def upgrade() -> None:
    """Upgrade schema."""
    for value in _NEW_LINK_TYPES:
        op.execute(f"ALTER TYPE product_link_type ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    """Downgrade schema."""
    # Note: Postgres does not support removing enum values.
    pass
