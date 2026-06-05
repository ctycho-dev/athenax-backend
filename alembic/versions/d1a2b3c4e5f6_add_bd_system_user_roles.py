"""add bd and system user roles

Revision ID: d1a2b3c4e5f6
Revises: b538f9785009
Create Date: 2026-06-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1a2b3c4e5f6'
down_revision: Union[str, Sequence[str], None] = 'b538f9785009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction, and a new enum value
    # cannot be used in the same transaction that adds it — isolate in an autocommit block.
    with op.get_context().autocommit_block():
        op.execute(sa.text("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'bd'"))
        op.execute(sa.text("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'system'"))


def downgrade() -> None:
    pass  # Postgres does not support removing enum values
