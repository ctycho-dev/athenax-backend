"""add paper_verification_status column to papers

Revision ID: f0ff203d8639
Revises: 47fb89c85fb6
Create Date: 2026-04-08 07:58:33.300669

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0ff203d8639'
down_revision: Union[str, Sequence[str], None] = '47fb89c85fb6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    paper_verification_status_enum = sa.Enum('pending', 'approved', 'rejected', name='paper_verification_status')
    paper_verification_status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'papers',
        sa.Column(
            'verification_status',
            sa.Enum('pending', 'approved', 'rejected', name='paper_verification_status', create_type=False),
            server_default='pending',
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('papers', 'verification_status')

    paper_verification_status_enum = sa.Enum('pending', 'approved', 'rejected', name='paper_verification_status')
    paper_verification_status_enum.drop(op.get_bind(), checkfirst=True)
