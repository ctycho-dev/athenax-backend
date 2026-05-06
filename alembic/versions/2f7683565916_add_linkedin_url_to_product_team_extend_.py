"""add linkedin_url and other_url to product_team, extend enums for stage and link_type

Revision ID: 2f7683565916
Revises: 23a6df604d20
Create Date: 2026-05-06 09:22:13.224894

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '2f7683565916'
down_revision: Union[str, Sequence[str], None] = '23a6df604d20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_STAGES = ("Launched", "Beta", "Active", "Active Development", "Acquired / Operating")
_NEW_LINK_TYPES = ("other",)


def upgrade() -> None:
    """Upgrade schema."""
    for value in _NEW_STAGES:
        op.execute(f"ALTER TYPE product_stage ADD VALUE IF NOT EXISTS '{value}'")

    for value in _NEW_LINK_TYPES:
        op.execute(f"ALTER TYPE product_link_type ADD VALUE IF NOT EXISTS '{value}'")

    op.execute("""
        ALTER TABLE product_team
            ADD COLUMN IF NOT EXISTS linkedin_url VARCHAR(200),
            ADD COLUMN IF NOT EXISTS other_url VARCHAR(200)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('product_team', 'other_url')
    op.drop_column('product_team', 'linkedin_url')
    # Note: Postgres does not support removing enum values.
