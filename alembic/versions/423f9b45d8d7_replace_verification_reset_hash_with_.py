"""replace verification reset hash with token hash type and add investor type enum

Revision ID: 423f9b45d8d7
Revises: 3a59f057be38
Create Date: 2026-03-26 13:08:58.950471

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '423f9b45d8d7'
down_revision: Union[str, Sequence[str], None] = '3a59f057be38'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create investor_type enum and migrate the column
    op.execute("CREATE TYPE investor_type AS ENUM ('VC', 'Angel', 'Corporate', 'Family Office')")
    op.execute(
        "ALTER TABLE investor_profiles ALTER COLUMN investor_type "
        "TYPE investor_type USING investor_type::investor_type"
    )
    # Replace verification_hash + reset_hash with token_hash + token_type
    op.add_column('users', sa.Column('token_hash', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('token_type', sa.String(length=20), nullable=True))
    op.drop_column('users', 'reset_hash')
    op.drop_column('users', 'verification_hash')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('users', sa.Column('verification_hash', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('reset_hash', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.drop_column('users', 'token_type')
    op.drop_column('users', 'token_hash')
    # Revert investor_type enum to plain varchar
    op.execute(
        "ALTER TABLE investor_profiles ALTER COLUMN investor_type "
        "TYPE VARCHAR(100) USING investor_type::text"
    )
    op.execute("DROP TYPE investor_type")
