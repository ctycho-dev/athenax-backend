"""add soft delete to products, articles, broadcasts

Revision ID: b538f9785009
Revises: c2f4638013ca
Create Date: 2026-05-27 12:37:34.754734

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b538f9785009'
down_revision: Union[str, Sequence[str], None] = 'c2f4638013ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('products', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('products', sa.Column('deleted_by_id', sa.Integer(), nullable=True))
    op.create_foreign_key('products_deleted_by_id_fkey', 'products', 'users', ['deleted_by_id'], ['id'], ondelete='SET NULL')
    op.add_column('articles', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('articles', sa.Column('deleted_by_id', sa.Integer(), nullable=True))
    op.create_foreign_key('articles_deleted_by_id_fkey', 'articles', 'users', ['deleted_by_id'], ['id'], ondelete='SET NULL')
    op.add_column('broadcasts', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('broadcasts', sa.Column('deleted_by_id', sa.Integer(), nullable=True))
    op.create_foreign_key('broadcasts_deleted_by_id_fkey', 'broadcasts', 'users', ['deleted_by_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('broadcasts_deleted_by_id_fkey', 'broadcasts', type_='foreignkey')
    op.drop_column('broadcasts', 'deleted_by_id')
    op.drop_column('broadcasts', 'deleted_at')
    op.drop_constraint('articles_deleted_by_id_fkey', 'articles', type_='foreignkey')
    op.drop_column('articles', 'deleted_by_id')
    op.drop_column('articles', 'deleted_at')
    op.drop_constraint('products_deleted_by_id_fkey', 'products', type_='foreignkey')
    op.drop_column('products', 'deleted_by_id')
    op.drop_column('products', 'deleted_at')
