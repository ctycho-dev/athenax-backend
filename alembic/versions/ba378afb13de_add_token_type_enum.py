"""add token_type enum

Revision ID: ba378afb13de
Revises: 423f9b45d8d7
Create Date: 2026-03-26 13:20:29.092247

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba378afb13de'
down_revision: Union[str, Sequence[str], None] = '423f9b45d8d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE TYPE token_type AS ENUM ('verification', 'reset')")
    op.execute(
        "ALTER TABLE users ALTER COLUMN token_type "
        "TYPE token_type USING token_type::token_type"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "ALTER TABLE users ALTER COLUMN token_type "
        "TYPE VARCHAR(20) USING token_type::text"
    )
    op.execute("DROP TYPE token_type")
