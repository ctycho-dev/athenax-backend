"""
Import Projects.xlsx into the database with status=PENDING.

Only new slugs are inserted — existing slugs are skipped unchanged.
No stale products are deleted.

Run validate_xlsx.py first to ensure the file is clean.

Usage:
    python scripts/upload_pending.py [path/to/file.xlsx]
"""

import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy import select

from app.database.connection import db_manager
from app.domain.category.model import Category
from app.domain.product.model import Product
from app.enums.enums import ProductStatus

from scripts.seed import (
    CATEGORY_ALIASES,
    XLSX_PATH,
    _insert_child_rows,
    _load_xlsx,
    _parse_row,
    _slug,
    _split,
    seed_categories,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


async def _ensure_subcategories(
    session,
    rows: list[dict],
    category_id_by_name: dict[str, int],
) -> None:
    """Create subcategories from xlsx that are not yet in the DB."""
    new_subs: dict[tuple[str, int], None] = {}
    for row in rows:
        raw_cat = row.get("category", "").strip()
        raw_cat = CATEGORY_ALIASES.get(raw_cat, raw_cat)
        parent_id = category_id_by_name.get(raw_cat)
        if parent_id is None:
            continue
        for sub_name in _split(row.get("subcategory", ""), ";"):
            if sub_name and sub_name not in category_id_by_name:
                new_subs[(sub_name, parent_id)] = None

    if not new_subs:
        return

    for sub_name, parent_id in new_subs:
        session.add(Category(name=sub_name, parent_id=parent_id))
    await session.flush()

    from sqlalchemy import select as _select
    result = await session.execute(
        _select(Category.id, Category.name).where(
            Category.name.in_([k[0] for k in new_subs])
        )
    )
    for rid, name in result.all():
        category_id_by_name[name] = rid
    log.info("  created %d new subcategories from xlsx", len(new_subs))


async def upload_pending(path: Path) -> None:
    if not path.exists():
        log.error("File not found: %s", path)
        sys.exit(1)

    log.info("Reading %s…", path)
    rows = _load_xlsx(path)
    log.info("  %d data rows found\n", len(rows))

    db_manager.init_engine()

    async with db_manager.session_scope() as session:
        category_id_by_name = await seed_categories(session)
        await _ensure_subcategories(session, rows, category_id_by_name)

        result = await session.execute(select(Product.slug))
        existing_slugs: set[str] = set(result.scalars().all())

        inserted = 0
        skipped = 0

        for row in rows:
            name = row["name"].strip()
            slug = _slug(name)

            if slug in existing_slugs:
                log.info("  SKIP    %s (slug already in DB)", name)
                skipped += 1
                continue

            existing_slugs.add(slug)
            parsed = _parse_row(row)

            product = Product(
                created_by_id=None,
                slug=slug,
                name=name,
                short_desc=parsed["short_desc"],
                description=parsed["description"],
                stage=parsed["stage"],
                founded=parsed["founded"],
                quality_badge=parsed["quality_badge"],
                email=parsed["email"],
                logo=parsed["logo"],
                imported=True,
                status=ProductStatus.PENDING,
            )
            session.add(product)
            await session.flush()
            _insert_child_rows(session, product.id, parsed, category_id_by_name)
            log.info("  INSERT  %s", name)
            inserted += 1

        await session.commit()

    await db_manager.close()
    log.info("\nDone — inserted: %d  skipped: %d", inserted, skipped)
    log.info("Products are pending. Approve via PATCH /v1/products/{id}/status.")


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else XLSX_PATH
    asyncio.run(upload_pending(target))
