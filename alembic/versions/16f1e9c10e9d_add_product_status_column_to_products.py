"""add product_status column to products

Revision ID: 16f1e9c10e9d
Revises: f3a1b2c4d5e6
Create Date: 2026-04-05 16:11:57.641030

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16f1e9c10e9d'
down_revision: Union[str, Sequence[str], None] = 'f3a1b2c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    product_status_enum = sa.Enum('pending', 'approved', 'rejected', name='product_status')
    product_status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'products',
        sa.Column(
            'status',
            sa.Enum('pending', 'approved', 'rejected', name='product_status', create_type=False),
            server_default='pending',
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('products', 'status')

    product_status_enum = sa.Enum('pending', 'approved', 'rejected', name='product_status')
    product_status_enum.drop(op.get_bind(), checkfirst=True)
