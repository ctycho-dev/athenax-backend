"""fix product sector and stage enum values to use display strings

Revision ID: f3a1b2c4d5e6
Revises: 237e08c1a744
Create Date: 2026-04-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3a1b2c4d5e6'
down_revision: Union[str, Sequence[str], None] = '237e08c1a744'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SECTOR_MAP = {
    'AI_AND_AGENTS': 'AI & Agents',
    'ROBOTICS': 'Robotics',
    'BIOTECH': 'Biotech',
    'CRYPTO_AND_DEFI': 'Crypto & DeFi',
    'DEVELOPER_TOOLS': 'Developer Tools',
    'INFRASTRUCTURE': 'Infrastructure',
    'CLIMATE_AND_ENERGY': 'Climate & Energy',
}

STAGE_MAP = {
    'PRE_SEED': 'Pre-Seed',
    'SEED': 'Seed',
    'SERIES_A': 'Series A',
    'SERIES_B': 'Series B',
}

NEW_SECTOR_VALUES = list(SECTOR_MAP.values())
NEW_STAGE_VALUES = list(STAGE_MAP.values())


def upgrade() -> None:
    op.add_column('products', sa.Column('sector_tmp', sa.Text(), nullable=True))
    op.add_column('products', sa.Column('stage_tmp', sa.Text(), nullable=True))

    conn = op.get_bind()
    for old, new in SECTOR_MAP.items():
        conn.execute(
            sa.text("UPDATE products SET sector_tmp = :new WHERE sector::text = :old"),
            {"new": new, "old": old},
        )
    for old, new in STAGE_MAP.items():
        conn.execute(
            sa.text("UPDATE products SET stage_tmp = :new WHERE stage::text = :old"),
            {"new": new, "old": old},
        )

    op.drop_column('products', 'sector')
    op.drop_column('products', 'stage')
    op.execute('DROP TYPE product_sector')
    op.execute('DROP TYPE product_stage')

    sa.Enum(*NEW_SECTOR_VALUES, name='product_sector').create(op.get_bind())
    sa.Enum(*NEW_STAGE_VALUES, name='product_stage').create(op.get_bind())

    op.add_column('products', sa.Column(
        'sector',
        sa.Enum(*NEW_SECTOR_VALUES, name='product_sector', create_type=False),
        nullable=True,
    ))
    op.add_column('products', sa.Column(
        'stage',
        sa.Enum(*NEW_STAGE_VALUES, name='product_stage', create_type=False),
        nullable=True,
    ))

    conn.execute(sa.text(
        "UPDATE products SET sector = sector_tmp::product_sector WHERE sector_tmp IS NOT NULL"
    ))
    conn.execute(sa.text(
        "UPDATE products SET stage = stage_tmp::product_stage WHERE stage_tmp IS NOT NULL"
    ))

    op.alter_column('products', 'sector', nullable=False)
    op.drop_column('products', 'sector_tmp')
    op.drop_column('products', 'stage_tmp')


def downgrade() -> None:
    op.add_column('products', sa.Column('sector_tmp', sa.Text(), nullable=True))
    op.add_column('products', sa.Column('stage_tmp', sa.Text(), nullable=True))

    conn = op.get_bind()
    for old, new in SECTOR_MAP.items():
        conn.execute(
            sa.text("UPDATE products SET sector_tmp = :old WHERE sector::text = :new"),
            {"old": old, "new": new},
        )
    for old, new in STAGE_MAP.items():
        conn.execute(
            sa.text("UPDATE products SET stage_tmp = :old WHERE stage::text = :new"),
            {"old": old, "new": new},
        )

    op.drop_column('products', 'sector')
    op.drop_column('products', 'stage')
    op.execute('DROP TYPE product_sector')
    op.execute('DROP TYPE product_stage')

    sa.Enum(*SECTOR_MAP.keys(), name='product_sector').create(op.get_bind())
    sa.Enum(*STAGE_MAP.keys(), name='product_stage').create(op.get_bind())

    op.add_column('products', sa.Column(
        'sector',
        sa.Enum(*SECTOR_MAP.keys(), name='product_sector', create_type=False),
        nullable=True,
    ))
    op.add_column('products', sa.Column(
        'stage',
        sa.Enum(*STAGE_MAP.keys(), name='product_stage', create_type=False),
        nullable=True,
    ))

    conn.execute(sa.text(
        "UPDATE products SET sector = sector_tmp::product_sector WHERE sector_tmp IS NOT NULL"
    ))
    conn.execute(sa.text(
        "UPDATE products SET stage = stage_tmp::product_stage WHERE stage_tmp IS NOT NULL"
    ))

    op.alter_column('products', 'sector', nullable=False)
    op.drop_column('products', 'sector_tmp')
    op.drop_column('products', 'stage_tmp')
