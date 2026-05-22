"""add is_hidden_from_all to categories

Revision ID: c43d4e7898a5
Revises: ac5d9c9a5e9d
Create Date: 2026-05-22 07:29:12.854174

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c43d4e7898a5'
down_revision: Union[str, Sequence[str], None] = 'ac5d9c9a5e9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('categories', sa.Column('is_hidden_from_all', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('categories', 'is_hidden_from_all')
