"""drop user university_id

Revision ID: 2c6a1a7b4d11
Revises: b5070e138eca
Create Date: 2026-03-20 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "2c6a1a7b4d11"
down_revision: Union[str, Sequence[str], None] = "b5070e138eca"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("users_university_id_fkey", "users", type_="foreignkey")
    op.drop_column("users", "university_id")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("users", sa.Column("university_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "users_university_id_fkey",
        "users",
        "universities",
        ["university_id"],
        ["id"],
    )
