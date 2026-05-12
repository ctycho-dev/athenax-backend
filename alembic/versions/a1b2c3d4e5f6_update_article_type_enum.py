"""update article_type enum to whitepaper, livestream, roundtable

Revision ID: a1b2c3d4e5f6
Revises: f78c5d76f902
Create Date: 2026-05-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f78c5d76f902'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

old_values = ('article', 'white_paper', 'recap')
new_values = ('whitepaper', 'livestream', 'roundtable')


def upgrade() -> None:
    op.execute("ALTER TYPE article_type RENAME TO article_type_old")
    op.execute("CREATE TYPE article_type AS ENUM('whitepaper', 'livestream', 'roundtable')")
    op.execute(
        "ALTER TABLE articles ALTER COLUMN article_type TYPE article_type "
        "USING article_type::text::article_type"
    )
    op.execute("DROP TYPE article_type_old")


def downgrade() -> None:
    op.execute("ALTER TYPE article_type RENAME TO article_type_new")
    op.execute("CREATE TYPE article_type AS ENUM('article', 'white_paper', 'recap')")
    op.execute(
        "ALTER TABLE articles ALTER COLUMN article_type TYPE article_type "
        "USING article_type::text::article_type"
    )
    op.execute("DROP TYPE article_type_new")
