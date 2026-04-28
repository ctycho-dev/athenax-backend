"""
Seed script for AthenaX database.

Usage:
    make seed
"""

import asyncio
import csv
import logging
import re
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import db_manager
from app.domain.category.model import Category
from app.domain.lab.model import Lab, LabCategory
from app.domain.product.model import Product, ProductCategory, ProductLink
from app.domain.university.model import University
from app.domain.user.model import User  # noqa: F401 — registers 'users' table in metadata
from app.enums.enums import ProductLinkType, ProductStage, ProductStatus

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

CSV_PATH = Path(__file__).parent.parent / "Projects.csv"

CATEGORIES: list[str] = [
    "AI & Agents",
    "Biotech",
    "Climate & Energy",
    "Crypto & DeFi",
    "Developer Tools",
    "Infrastructure",
    "Robotics",
]

# Normalize CSV category names that differ from canonical CATEGORIES values
CATEGORY_ALIASES: dict[str, str] = {
    "Crypto": "Crypto & DeFi",
}


def _load_csv() -> list[dict]:
    """Read the CSV once, filtering out rows with no project name."""
    with open(CSV_PATH, newline="", encoding="utf-8") as fh:
        return [
            row for row in csv.DictReader(fh)
            if row.get("Project Name", "").strip()
        ]

# key → {country (ISO 3166-1 alpha-3), focus}
UNIVERSITIES: dict[str, dict] = {
    "MIT":             {"country": "USA", "focus": "Engineering and applied cryptography"},
    "Oxford":          {"country": "GBR", "focus": "Internet governance and policy"},
    "Harvard":         {"country": "USA", "focus": "Economics and public policy"},
    "Stanford":        {"country": "USA", "focus": "Distributed systems and security"},
    "Caltech":         {"country": "USA", "focus": "Computer science and mathematics"},
    "Cambridge":       {"country": "GBR", "focus": "Digital society and governance"},
    "ETH Zurich":      {"country": "CHE", "focus": "Cryptography and protocol engineering"},
    "Imperial College":{"country": "GBR", "focus": "Systems engineering and computing"},
    "Columbia":        {"country": "USA", "focus": "Applied computer science"},
}

# university_key must match a key in UNIVERSITIES
LABS: list[dict] = [
    {
        "name":           "IF Labs",
        "university_key": "MIT",
        "focus":          "Frontier Infrastructure & Protocol Research",
        "description":    (
            "IF Labs is the founding research partner of AthenaX, specialising in "
            "applied onchain infrastructure research with a focus on zero-knowledge "
            "proofs, Layer 2 scaling, and DeFi protocol design."
        ),
        "active":         True,
        "categories":     ["Infrastructure", "Crypto & DeFi"],
    },
    {
        "name":           "MIT DCI",
        "university_key": "MIT",
        "focus":          "Digital Currency Initiative",
        "description":    (
            "The MIT Digital Currency Initiative bridges academic research and "
            "practical implementation of digital currencies and decentralised systems."
        ),
        "active":         True,
        "categories":     ["Crypto & DeFi"],
    },
    {
        "name":           "Stanford Blockchain",
        "university_key": "Stanford",
        "focus":          "Blockchain Protocol Research",
        "description":    (
            "Stanford's Blockchain Research Center conducts fundamental research in "
            "distributed systems, cryptography, and decentralised protocol design."
        ),
        "active":         True,
        "categories":     ["Infrastructure"],
    },
    {
        "name":           "Oxford Internet Institute",
        "university_key": "Oxford",
        "focus":          "Internet & Society Research",
        "description":    (
            "The OII examines the social, economic, and political implications of "
            "internet technologies and decentralised governance systems."
        ),
        "active":         False,
        "categories":     ["AI & Agents"],
    },
    {
        "name":           "Ethereum Foundation Research",
        "university_key": "ETH Zurich",
        "focus":          "Ethereum Protocol Development",
        "description":    (
            "The EF Research team drives the technical evolution of the Ethereum "
            "protocol — consensus, data availability, execution, and beyond."
        ),
        "active":         True,
        "categories":     ["Infrastructure", "Crypto & DeFi"],
    },
    {
        "name":           "Consensys R&D",
        "university_key": "Columbia",
        "focus":          "Applied Protocol Engineering",
        "description":    (
            "Consensys R&D combines protocol engineering with applied research "
            "across the Ethereum ecosystem."
        ),
        "active":         True,
        "categories":     ["Developer Tools", "Infrastructure"],
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def upsert_simple(
    session: AsyncSession,
    name_col,
    id_col,
    names: list[str],
    build,
    label: str,
) -> dict[str, int]:
    """
    Generic idempotent insert for models keyed by a single name column.

    Fetches all existing rows in one query, inserts only the missing ones via
    `build(name)`, flushes, then returns {name: id} for every row.
    """
    existing: dict[str, int] = {
        name: row_id
        for row_id, name in (await session.execute(select(id_col, name_col))).all()
    }
    new_names = [n for n in names if n not in existing]

    if new_names:
        for name in new_names:
            session.add(build(name))
        await session.flush()
        new_rows = (
            await session.execute(select(id_col, name_col).where(name_col.in_(new_names)))
        ).all()
        existing.update({name: row_id for row_id, name in new_rows})
        log.info("  [%s] seeded %d: %s", label, len(new_names), new_names)
    else:
        log.info("  [%s] all present, skipping", label)

    return existing


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------

async def seed_categories(session: AsyncSession) -> dict[str, int]:
    return await upsert_simple(
        session,
        name_col=Category.name,
        id_col=Category.id,
        names=CATEGORIES,
        build=lambda name: Category(name=name),
        label="categories",
    )


async def seed_universities(session: AsyncSession) -> dict[str, int]:
    return await upsert_simple(
        session,
        name_col=University.name,
        id_col=University.id,
        names=list(UNIVERSITIES),
        build=lambda name: University(
            name=name,
            country=UNIVERSITIES[name]["country"],
            focus=UNIVERSITIES[name]["focus"],
        ),
        label="universities",
    )


async def seed_labs(
    session: AsyncSession,
    university_id_by_name: dict[str, int],
    category_id_by_name: dict[str, int],
) -> None:
    """Insert missing labs and their category associations."""
    existing = set((await session.execute(select(Lab.name))).scalars().all())
    pending: list[tuple[Lab, list[str]]] = []

    for lab in LABS:
        if lab["name"] in existing:
            continue

        university_id = university_id_by_name.get(lab["university_key"])
        if university_id is None:
            log.warning(
                "  [labs] unknown university key %r for lab %r — skipping",
                lab["university_key"], lab["name"],
            )
            continue

        new_lab = Lab(
            name=lab["name"],
            university_id=university_id,
            focus=lab["focus"],
            description=lab["description"],
            active=lab["active"],
        )
        session.add(new_lab)
        pending.append((new_lab, lab["categories"]))

    if pending:
        await session.flush()  # one flush to get all IDs at once
        for new_lab, cat_names in pending:
            _link_categories(session, new_lab.id, cat_names, category_id_by_name, LabCategory, "lab_id", "labs")
        log.info("  [labs] seeded %d: %s", len(pending), [lab.name for lab, _ in pending])
    else:
        log.info("  [labs] all present, skipping")


def _slug(name: str) -> str:
    """Convert a product name to a URL-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", name.lower().strip())
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug[:150]


def _link_categories(
    session: AsyncSession,
    entity_id: int,
    cat_names: list[str],
    category_id_by_name: dict[str, int],
    AssocModel,
    fk_field: str,
    label: str,
) -> None:
    """Add category association rows for a single entity."""
    for cat_name in cat_names:
        cat_id = category_id_by_name.get(cat_name)
        if cat_id is None:
            log.warning("  [%s] unknown category %r — skipping", label, cat_name)
            continue
        session.add(AssocModel(**{fk_field: entity_id, "category_id": cat_id}))


_STAGE_MAP: dict[str, ProductStage] = {s.value.lower(): s for s in ProductStage}


async def seed_products(
    session: AsyncSession,
    rows: list[dict],
    category_id_by_name: dict[str, int],
) -> None:
    """Insert products from the CSV, skipping any that already exist by slug."""
    existing_slugs: set[str] = set(
        (await session.execute(select(Product.slug))).scalars().all()
    )

    new_products: list[tuple[Product, str | None, str | None, str | None]] = []
    for row in rows:
        name = row["Project Name"].strip()
        slug = _slug(name)
        if slug in existing_slugs:
            continue
        existing_slugs.add(slug)

        raw_year = row.get("Year", "").strip()
        website = row.get("Website / github / demo", "").strip() or None
        github = row.get("GitHub Rep", "").strip() or None
        product = Product(
            created_by_id=None,
            slug=slug,
            name=name,
            description=row.get("One Line Description", "").strip() or None,
            founded=int(raw_year) if raw_year.isdigit() else None,
            stage=_STAGE_MAP.get(row.get("Stage", "").strip().lower()),
            email=row.get("Email", "").strip() or None,
            twitter=row.get("Twitter", "").strip() or None,
            logo=row.get("Logo", "").strip() or None,
            imported=True,
            status=ProductStatus.APPROVED,
        )
        session.add(product)
        raw_cat = row.get("Main Category", "").strip() or None
        cat = CATEGORY_ALIASES.get(raw_cat, raw_cat) if raw_cat else None
        new_products.append((product, cat, website, github))

    if not new_products:
        log.info("  [products] all present, skipping")
        return

    await session.flush()

    for product, raw_cat, website, github in new_products:
        if raw_cat:
            _link_categories(session, product.id, [raw_cat], category_id_by_name, ProductCategory, "product_id", "products")
        if website:
            session.add(ProductLink(product_id=product.id, link_type=ProductLinkType.WEBSITE, url=website))
        if github:
            session.add(ProductLink(product_id=product.id, link_type=ProductLinkType.GITHUB, url=github))

    log.info("  [products] seeded %d products", len(new_products))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    log.info("Starting seed…")
    db_manager.init_engine()

    rows = _load_csv()

    async with db_manager.session_scope() as session:
        category_id_by_name = await seed_categories(session)
        university_id_by_name = await seed_universities(session)
        await seed_labs(session, university_id_by_name, category_id_by_name)
        await seed_products(session, rows, category_id_by_name)
        await session.commit()

    await db_manager.close()
    log.info("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
