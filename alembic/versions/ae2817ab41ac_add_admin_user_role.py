"""add admin user role

Revision ID: ae2817ab41ac
Revises: ecc46b3d037f
Create Date: 2026-03-25 07:24:06.399096

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'ae2817ab41ac'
down_revision: Union[str, Sequence[str], None] = 'ecc46b3d037f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'admin';")


def downgrade() -> None:
    """Downgrade schema."""
    # PostgreSQL enum values cannot be removed safely in-place.
    # Keeping downgrade as a no-op to avoid destructive type rebuilds.
    pass
