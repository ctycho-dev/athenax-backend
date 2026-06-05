"""seed system user

Revision ID: e2b3c4d5f6a7
Revises: d1a2b3c4e5f6
Create Date: 2026-06-04 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2b3c4d5f6a7'
down_revision: Union[str, Sequence[str], None] = 'd1a2b3c4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Keep in sync with app.enums.enums.SYSTEM_USER_EMAIL
SYSTEM_USER_EMAIL = "system@athenax.internal"


def upgrade() -> None:
    # System user owns records created via internal endpoints. password_hash='!' is a
    # literal, unhashed placeholder that can never match a bcrypt check; verified=false
    # ("active false") so it can never authenticate via the normal login flow.
    op.execute(
        sa.text(
            """
            INSERT INTO users (name, email, password_hash, verified, role, created_at, updated_at)
            VALUES ('System', :email, '!', false, 'system', now(), now())
            ON CONFLICT (email) DO NOTHING
            """
        ).bindparams(email=SYSTEM_USER_EMAIL)
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM users WHERE email = :email").bindparams(email=SYSTEM_USER_EMAIL)
    )
