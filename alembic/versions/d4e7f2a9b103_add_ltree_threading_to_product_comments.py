"""add ltree threading to product comments

Revision ID: d4e7f2a9b103
Revises: 2f7683565916
Create Date: 2026-05-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e7f2a9b103'
down_revision: Union[str, Sequence[str], None] = '2f7683565916'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS ltree")

    op.add_column('product_comments', sa.Column('parent_id', sa.Integer(), nullable=True))
    op.execute("ALTER TABLE product_comments ADD COLUMN path ltree")

    op.execute(
        "CREATE INDEX ix_product_comments_path_gist ON product_comments USING GIST (path)"
    )

    op.create_foreign_key(
        'fk_product_comments_parent',
        'product_comments', 'product_comments',
        ['parent_id'], ['id'],
        ondelete='CASCADE',
    )

    # Backfill existing root comments: path = their own id as an ltree label
    op.execute("UPDATE product_comments SET path = id::text::ltree WHERE parent_id IS NULL")


def downgrade() -> None:
    op.drop_constraint('fk_product_comments_parent', 'product_comments', type_='foreignkey')
    op.execute("DROP INDEX IF EXISTS ix_product_comments_path_gist")
    op.execute("ALTER TABLE product_comments DROP COLUMN IF EXISTS path")
    op.drop_column('product_comments', 'parent_id')
