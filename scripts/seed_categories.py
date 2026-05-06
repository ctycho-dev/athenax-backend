"""
Seed parent categories and their subcategories from Categories.csv.

Usage:
    make seed:categories
"""

import asyncio
import csv
import logging
from pathlib import Path

from sqlalchemy import select

from app.database.connection import db_manager
from app.domain.category.model import Category
from app.domain.user.model import User  # noqa: F401 — registers metadata

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

CATEGORIES_CSV_PATH = Path(__file__).parent.parent / "Categories.csv"

# Parents guaranteed to exist even if absent from the CSV
BASELINE_PARENTS: list[str] = [
    "AI & Agents",
    "Biotech",
    "Climate & Energy",
    "Crypto & DeFi",
    "Developer Tools",
    "Infrastructure",
    "Robotics",
]


def _load_category_tree() -> dict[str, list[str]]:
    """Return {parent_name: [sub_name, ...]} parsed from Categories.csv."""
    tree: dict[str, list[str]] = {}
    with open(CATEGORIES_CSV_PATH, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            parent = row.get("Category", "").strip()
            sub = row.get("Sub-Category", "").strip()
            if not parent:
                continue
            if parent not in tree:
                tree[parent] = []
            if sub and sub not in tree[parent]:
                tree[parent].append(sub)
    return tree


async def seed_categories() -> None:
    db_manager.init_engine()

    tree = _load_category_tree()
    all_parents = list(dict.fromkeys(list(tree.keys()) + BASELINE_PARENTS))

    async with db_manager.session_scope() as session:
        # --- Pass 1: parents ---
        result = await session.execute(
            select(Category.id, Category.name).where(Category.parent_id.is_(None))
        )
        existing_parents: dict[str, int] = {name: row_id for row_id, name in result.all()}

        new_parents = [n for n in all_parents if n not in existing_parents]
        if new_parents:
            for name in new_parents:
                session.add(Category(name=name))
            await session.flush()
            rows = await session.execute(
                select(Category.id, Category.name).where(
                    Category.name.in_(new_parents), Category.parent_id.is_(None)
                )
            )
            existing_parents.update({name: row_id for row_id, name in rows.all()})
            log.info("  [categories] seeded %d parents: %s", len(new_parents), new_parents)
        else:
            log.info("  [categories] all parents present, skipping")

        # --- Pass 2: subcategories ---
        result = await session.execute(
            select(Category.id, Category.name, Category.parent_id).where(
                Category.parent_id.is_not(None)
            )
        )
        existing_subs: dict[tuple[str, int], int] = {
            (name, parent_id): row_id for row_id, name, parent_id in result.all()
        }

        new_subs: list[tuple[str, int]] = []
        for parent_name, sub_names in tree.items():
            parent_id = existing_parents.get(parent_name)
            if parent_id is None:
                log.warning("  [categories] parent %r not found, skipping subcategories", parent_name)
                continue
            for sub_name in sub_names:
                if (sub_name, parent_id) not in existing_subs:
                    new_subs.append((sub_name, parent_id))

        if new_subs:
            for sub_name, parent_id in new_subs:
                session.add(Category(name=sub_name, parent_id=parent_id))
            log.info("  [categories] seeded %d subcategories", len(new_subs))
        else:
            log.info("  [categories] all subcategories present, skipping")

        await session.commit()

    await db_manager.close()
    log.info("Category seed complete.")


if __name__ == "__main__":
    asyncio.run(seed_categories())
