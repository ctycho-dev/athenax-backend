"""
Validate Projects.xlsx then import as pending — single command.

Validates every row against Data Specs rules first.
If any errors are found the import is aborted and nothing is written to the DB.
If clean, products are inserted with status=PENDING (invisible until admin approves).
Existing slugs are skipped silently.

Usage:
    python scripts/import_products.py [path/to/file.xlsx]
"""

import asyncio
import logging
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import openpyxl
from sqlalchemy import select

from app.database.connection import db_manager
from app.domain.category.model import Category
from app.domain.product.model import Product
from app.enums.enums import ProductLinkType, ProductStage, ProductStatus, VerificationStatus

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

# ---------------------------------------------------------------------------
# Validation rules
# ---------------------------------------------------------------------------

VALID_STAGES = {s.value for s in ProductStage}
FORBIDDEN_EMPTY = {"n/a", "-", "none"}
URL_COLUMNS = {"logo", "twitter", "website", "discord", "docs", "other link", "github"}
PLAIN_TEXT_COLUMNS = {"name", "short_desc", "description", "quality_badge", "category"}
PACKED_MIN_FIELDS = {"team": 1, "voices": 4, "bounties": 4}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
YEAR_RE = re.compile(r"^\d{4}$")
FUNDING_RE = re.compile(r"^\d+(\.\d+)?$")


def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v).strip()


def _check_row(row_num: int, name: str, row: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    prefix = f"row {row_num:<3} [{name}]"

    def err(col: str, msg: str) -> None:
        errors.append(f"  {prefix}  ERROR    {col}: {msg}")

    def warn(col: str, msg: str) -> None:
        warnings.append(f"  {prefix}  WARNING  {col}: {msg}")

    for col, val in row.items():
        if not col or not val:
            continue
        if val.strip().lower() in FORBIDDEN_EMPTY:
            err(col, f"leave blank instead of {val!r}")
            continue
        if col in PLAIN_TEXT_COLUMNS:
            if "|" in val:
                err(col, "must not contain '|'")
            if ";" in val:
                err(col, "must not contain ';'")
        if col in URL_COLUMNS:
            if not val.startswith("https://"):
                err(col, f"must start with https://, got {val!r}")
        if col == "funding" and val:
            if not FUNDING_RE.match(val.strip()):
                err(col, f"digits only (no $, commas, spaces), got {val!r}")
        if col == "founded" and val:
            stripped = val.strip()
            if not YEAR_RE.match(stripped) or not (1900 <= int(stripped) <= 2099):
                err(col, f"must be a 4-digit year 1900–2099, got {val!r}")
        if col == "stage" and val:
            if val.strip() not in VALID_STAGES:
                err(col, f"{val!r} not valid — choose: {', '.join(sorted(VALID_STAGES))}")
        if col == "email" and val:
            if not EMAIL_RE.match(val.strip()):
                err(col, f"invalid email: {val!r}")
        if col in PACKED_MIN_FIELDS:
            min_fields = PACKED_MIN_FIELDS[col]
            for i, entry in enumerate([e.strip() for e in val.split(";") if e.strip()], start=1):
                parts = [p.strip() for p in entry.split("|")]
                if col == "team" and not parts[0]:
                    warn(col, f"entry {i}: name is empty")
                if len(parts) < min_fields:
                    warn(col, f"entry {i}: expected {min_fields}+ pipe-separated fields, got {len(parts)}")
    return errors, warnings


def validate(path: Path) -> bool:
    """Return True if file is valid (zero errors), False otherwise."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    all_rows = list(ws.iter_rows(values_only=True))
    wb.close()

    headers = [str(h).strip().lower() if h is not None else "" for h in all_rows[0]]

    all_errors: list[str] = []
    all_warnings: list[str] = []
    seen_slugs: dict[str, int] = {}
    data_rows = 0

    for row_num, raw in enumerate(all_rows[1:], start=2):
        row = {headers[i]: _cell(v) for i, v in enumerate(raw) if i < len(headers) and headers[i]}
        name = row.get("name", "").strip()
        if not name:
            continue

        data_rows += 1
        errs, warns = _check_row(row_num, name, row)
        all_errors.extend(errs)
        all_warnings.extend(warns)

        slug = re.sub(r"[^\w\s-]", "", name.lower().strip())
        slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
        if slug in seen_slugs:
            all_warnings.append(
                f"  row {row_num:<3} [{name}]  WARNING  name: duplicate slug (same as row {seen_slugs[slug]})"
            )
        else:
            seen_slugs[slug] = row_num

    print(f"Validated {data_rows} rows from {path.name}\n")

    if all_errors:
        print("--- ERRORS ---")
        for line in all_errors:
            print(line)
        print()
    if all_warnings:
        print("--- WARNINGS ---")
        for line in all_warnings:
            print(line)
        print()

    summary = f"{len(all_errors)} error(s), {len(all_warnings)} warning(s)"
    if all_errors:
        print(f"✗ {summary} — fix errors before importing.\n")
        return False

    print(f"✓ {summary} — validation passed.\n")
    return True


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

async def _ensure_subcategories(session, rows: list[dict], category_id_by_name: dict[str, int]) -> None:
    new_subs: dict[tuple[str, int], None] = {}
    for row in rows:
        raw_cat = CATEGORY_ALIASES.get(row.get("category", "").strip(), row.get("category", "").strip())
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

    result = await session.execute(
        select(Category.id, Category.name).where(Category.name.in_([k[0] for k in new_subs]))
    )
    for rid, name in result.all():
        category_id_by_name[name] = rid
    log.info("  created %d new subcategories", len(new_subs))


async def upload(path: Path) -> None:
    rows = _load_xlsx(path)
    log.info("Importing %d products…\n", len(rows))

    db_manager.init_engine()

    async with db_manager.session_scope() as session:
        category_id_by_name = await seed_categories(session)
        await _ensure_subcategories(session, rows, category_id_by_name)

        existing_slugs: set[str] = set((await session.execute(select(Product.slug))).scalars().all())

        inserted = 0
        skipped = 0
        base_time = datetime.now(timezone.utc)
        insert_index = 0

        for row in rows:
            name = row["name"].strip()
            slug = _slug(name)

            if slug in existing_slugs:
                log.info("  SKIP    %s", name)
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
                created_at=base_time + timedelta(seconds=insert_index),
            )
            session.add(product)
            await session.flush()
            _insert_child_rows(session, product.id, parsed, category_id_by_name)
            log.info("  INSERT  %s", name)
            inserted += 1
            insert_index += 1

        await session.commit()

    await db_manager.close()
    log.info("\nDone — inserted: %d  skipped: %d", inserted, skipped)
    log.info("Approve via PATCH /v1/products/{id}/status  { \"status\": \"approved\" }")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main(path: Path) -> None:
    if not path.exists():
        print(f"ERROR: file not found: {path}")
        sys.exit(1)

    print(f"--- Step 1: Validate ---\n")
    if not validate(path):
        sys.exit(1)

    print(f"--- Step 2: Import ---\n")
    await upload(path)


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else XLSX_PATH
    asyncio.run(main(target))
