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

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import db_manager
from app.domain.category.model import Category
from app.domain.lab.model import Lab, LabCategory
from app.domain.product.model import (
    Product,
    ProductBacker,
    ProductCategory,
    ProductLink,
    ProductTeamMember,
    ProductVoice,
)
from app.domain.university.model import University
from app.domain.user.model import User  # noqa: F401 — registers 'users' table in metadata
from app.enums.enums import ProductLinkType, ProductStage, ProductStatus, VerificationStatus

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

CSV_PATH = Path(__file__).parent.parent / "Projects.csv"
CATEGORIES_CSV_PATH = Path(__file__).parent.parent / "Categories.csv"


# ---------------------------------------------------------------------------
# Hard-coded seed data (labs / universities)
# ---------------------------------------------------------------------------

CATEGORIES: list[str] = [
    "AI & Agents",
    "Biotech",
    "Climate & Energy",
    "Crypto & DeFi",
    "Developer Tools",
    "Infrastructure",
    "Robotics",
]

CATEGORY_ALIASES: dict[str, str] = {
    "Crypto":       "Crypto & DeFi",
    "Robotics / AI": "Robotics",
    "Biotech / AI": "Biotech",
}

UNIVERSITIES: dict[str, dict] = {
    "MIT":              {"country": "USA", "focus": "Engineering and applied cryptography"},
    "Oxford":           {"country": "GBR", "focus": "Internet governance and policy"},
    "Harvard":          {"country": "USA", "focus": "Economics and public policy"},
    "Stanford":         {"country": "USA", "focus": "Distributed systems and security"},
    "Caltech":          {"country": "USA", "focus": "Computer science and mathematics"},
    "Cambridge":        {"country": "GBR", "focus": "Digital society and governance"},
    "ETH Zurich":       {"country": "CHE", "focus": "Cryptography and protocol engineering"},
    "Imperial College": {"country": "GBR", "focus": "Systems engineering and computing"},
    "Columbia":         {"country": "USA", "focus": "Applied computer science"},
}

LABS: list[dict] = [
    {
        "name":           "IF Labs",
        "university_key": "MIT",
        "focus":          "Frontier Infrastructure & Protocol Research",
        "description": (
            "IF Labs is the founding research partner of AthenaX, specialising in "
            "applied onchain infrastructure research with a focus on zero-knowledge "
            "proofs, Layer 2 scaling, and DeFi protocol design."
        ),
        "active":     True,
        "categories": ["Infrastructure", "Crypto & DeFi"],
    },
    {
        "name":           "MIT DCI",
        "university_key": "MIT",
        "focus":          "Digital Currency Initiative",
        "description": (
            "The MIT Digital Currency Initiative bridges academic research and "
            "practical implementation of digital currencies and decentralised systems."
        ),
        "active":     True,
        "categories": ["Crypto & DeFi"],
    },
    {
        "name":           "Stanford Blockchain",
        "university_key": "Stanford",
        "focus":          "Blockchain Protocol Research",
        "description": (
            "Stanford's Blockchain Research Center conducts fundamental research in "
            "distributed systems, cryptography, and decentralised protocol design."
        ),
        "active":     True,
        "categories": ["Infrastructure"],
    },
    {
        "name":           "Oxford Internet Institute",
        "university_key": "Oxford",
        "focus":          "Internet & Society Research",
        "description": (
            "The OII examines the social, economic, and political implications of "
            "internet technologies and decentralised governance systems."
        ),
        "active":     False,
        "categories": ["AI & Agents"],
    },
    {
        "name":           "Ethereum Foundation Research",
        "university_key": "ETH Zurich",
        "focus":          "Ethereum Protocol Development",
        "description": (
            "The EF Research team drives the technical evolution of the Ethereum "
            "protocol — consensus, data availability, execution, and beyond."
        ),
        "active":     True,
        "categories": ["Infrastructure", "Crypto & DeFi"],
    },
    {
        "name":           "Consensys R&D",
        "university_key": "Columbia",
        "focus":          "Applied Protocol Engineering",
        "description": (
            "Consensys R&D combines protocol engineering with applied research "
            "across the Ethereum ecosystem."
        ),
        "active":     True,
        "categories": ["Developer Tools", "Infrastructure"],
    },
]


# ---------------------------------------------------------------------------
# Stage map — covers both old funding-style and new lifecycle-style values
# ---------------------------------------------------------------------------

_STAGE_MAP: dict[str, ProductStage] = {s.value.lower(): s for s in ProductStage}


# ---------------------------------------------------------------------------
# CSV loaders
# ---------------------------------------------------------------------------

def _load_category_tree() -> dict[str, list[str]]:
    """Parse Categories.csv → {parent_name: [sub_name, ...]}."""
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


def _load_csv() -> list[dict]:
    """Read Projects.csv, drop rows with no name."""
    with open(CSV_PATH, newline="", encoding="utf-8") as fh:
        return [row for row in csv.DictReader(fh) if row.get("name", "").strip()]


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _split(raw: str, sep: str = ";") -> list[str]:
    """Split a multi-value cell by sep, strip, drop empties."""
    return [p.strip() for p in raw.split(sep) if p.strip()]


def _slug(name: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", name.lower().strip())
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug[:150]


def _classify_url(url: str) -> str:
    """Return the team member URL field name based on the domain."""
    if not url.startswith("http"):
        return "other_url"
    if "linkedin.com" in url:
        return "linkedin_url"
    if "twitter.com" in url or "x.com" in url:
        return "twitter_url"
    if "github.com" in url:
        return "github_url"
    return "other_url"


def _parse_team(raw: str) -> list[dict]:
    """
    Parse the team cell.

    Each member entry is pipe-separated:
      name | role | bio | url [| url ...]

    URLs after the bio are classified by domain into linkedin_url, twitter_url,
    github_url, or other_url. Members are semicolon-separated. A semicolon
    inside a bio (no pipe in the segment) is re-joined to the previous member.
    """
    raw_segments = [s.strip() for s in raw.split(";") if s.strip()]
    merged: list[str] = []
    for seg in raw_segments:
        if "|" not in seg and merged:
            merged[-1] = merged[-1] + "; " + seg
        else:
            merged.append(seg)

    members = []
    for entry in merged:
        parts = [p.strip() for p in entry.split("|")]
        if not parts or not parts[0]:
            continue
        member: dict = {
            "name":         parts[0][:100],
            "role_label":   parts[1][:150] if len(parts) > 1 else None,
            "bio_note":     parts[2][:300] if len(parts) > 2 else None,
            "linkedin_url": None,
            "twitter_url":  None,
            "github_url":   None,
            "other_url":    None,
        }
        for url in parts[3:]:
            if not url.startswith("http"):
                continue
            field = _classify_url(url)
            if member[field] is None:  # first URL wins per type
                member[field] = url
        members.append(member)
    return members


def _parse_backers(raw: str) -> list[str]:
    return _split(raw, ";")


def _parse_press_urls(raw: str) -> list[str]:
    """Voices column holds press article URLs separated by semicolons."""
    return [u for u in _split(raw, ";") if u.startswith("http")]


# ---------------------------------------------------------------------------
# Generic upsert helper
# ---------------------------------------------------------------------------

async def upsert_simple(
    session: AsyncSession,
    name_col,
    id_col,
    names: list[str],
    build,
    label: str,
) -> dict[str, int]:
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
            await session.execute(
                select(id_col, name_col).where(name_col.in_(new_names))
            )
        ).all()
        existing.update({name: row_id for row_id, name in new_rows})
        log.info("  [%s] seeded %d: %s", label, len(new_names), new_names)
    else:
        log.info("  [%s] all present, skipping", label)
    return existing


# ---------------------------------------------------------------------------
# Seed: categories
# ---------------------------------------------------------------------------

async def seed_categories(session: AsyncSession) -> dict[str, int]:
    """
    Seed parent categories then subcategories from Categories.csv.

    Returns a flat {name: id} map. For subcategories the key is the sub name;
    parents take precedence on name collision.

    Also returns a separate sub-lookup keyed by (sub_name, parent_id) so the
    product seeder can match subcategories to the correct parent.
    """
    tree = _load_category_tree()
    all_parents = list(dict.fromkeys(list(tree.keys()) + CATEGORIES))

    # --- Pass 1: parents ---
    result = await session.execute(
        select(Category.id, Category.name).where(Category.parent_id.is_(None))
    )
    existing_parents: dict[str, int] = {name: rid for rid, name in result.all()}

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
        existing_parents.update({name: rid for rid, name in rows.all()})
        log.info("  [categories] seeded %d parents: %s", len(new_parents), new_parents)
    else:
        log.info("  [categories] all parents present, skipping")

    # --- Pass 2: subcategories ---
    result = await session.execute(
        select(Category.id, Category.name, Category.parent_id).where(
            Category.parent_id.is_not(None)
        )
    )
    # (sub_name, parent_id) → sub_id
    existing_subs: dict[tuple[str, int], int] = {
        (name, parent_id): rid for rid, name, parent_id in result.all()
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
        await session.flush()
        rows = await session.execute(
            select(Category.id, Category.name, Category.parent_id).where(
                Category.parent_id.is_not(None)
            )
        )
        for rid, name, parent_id in rows.all():
            existing_subs[(name, parent_id)] = rid
        log.info("  [categories] seeded %d subcategories", len(new_subs))
    else:
        log.info("  [categories] all subcategories present, skipping")

    # Flat name → id (parents win on collision)
    name_to_id: dict[str, int] = {name: rid for (name, _), rid in existing_subs.items()}
    name_to_id.update(existing_parents)

    return name_to_id


# ---------------------------------------------------------------------------
# Seed: universities
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Seed: labs
# ---------------------------------------------------------------------------

async def seed_labs(
    session: AsyncSession,
    university_id_by_name: dict[str, int],
    category_id_by_name: dict[str, int],
) -> None:
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
        await session.flush()
        for new_lab, cat_names in pending:
            _link_categories(
                session, new_lab.id, cat_names, category_id_by_name,
                LabCategory, "lab_id", "labs",
            )
        log.info("  [labs] seeded %d: %s", len(pending), [lab.name for lab, _ in pending])
    else:
        log.info("  [labs] all present, skipping")


# ---------------------------------------------------------------------------
# Category linking helper
# ---------------------------------------------------------------------------

def _link_categories(
    session: AsyncSession,
    entity_id: int,
    cat_names: list[str],
    category_id_by_name: dict[str, int],
    AssocModel,
    fk_field: str,
    label: str,
) -> None:
    for cat_name in cat_names:
        cat_id = category_id_by_name.get(cat_name)
        if cat_id is None:
            log.warning("  [%s] unknown category %r — skipping", label, cat_name)
            continue
        session.add(AssocModel(**{fk_field: entity_id, "category_id": cat_id}))


# ---------------------------------------------------------------------------
# Seed: products
# ---------------------------------------------------------------------------

async def seed_products(
    session: AsyncSession,
    rows: list[dict],
    category_id_by_name: dict[str, int],
) -> None:
    """
    Upsert products from the CSV.

    For each row:
    - New slug  → insert product + all child rows.
    - Existing  → update scalar fields (keep name/slug/logo), then delete and
                  re-insert all child rows (links, team, backers, categories).
    """
    # --- Pass 0: create any subcategories from the CSV not yet in the DB ---
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

    if new_subs:
        for sub_name, parent_id in new_subs:
            session.add(Category(name=sub_name, parent_id=parent_id))
        await session.flush()
        sub_result = await session.execute(
            select(Category.id, Category.name).where(
                Category.name.in_([k[0] for k in new_subs])
            )
        )
        for rid, name in sub_result.all():
            category_id_by_name[name] = rid
        log.info("  [products] seeded %d new subcategories from Projects.csv", len(new_subs))

    # Fetch existing products keyed by slug
    result = await session.execute(select(Product.id, Product.slug, Product.logo))
    existing_by_slug: dict[str, tuple[int, str | None]] = {
        slug: (pid, logo) for pid, slug, logo in result.all()
    }

    new_products: list[tuple[Product, dict]] = []
    update_products: list[tuple[int, dict]] = []  # (product_id, row)

    seen_slugs: set[str] = set()
    for row in rows:
        name = row["name"].strip()
        slug = _slug(name)
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        parsed = _parse_row(row)

        if slug in existing_by_slug:
            product_id, existing_logo = existing_by_slug[slug]
            update_products.append((product_id, parsed, existing_logo))
        else:
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
                imported=True,
                status=ProductStatus.APPROVED,
            )
            session.add(product)
            new_products.append((product, parsed))

    # --- Insert new products ---
    if new_products:
        await session.flush()
        for product, parsed in new_products:
            _insert_child_rows(session, product.id, parsed, category_id_by_name)
        log.info("  [products] inserted %d new products", len(new_products))
    else:
        log.info("  [products] no new products to insert")

    # --- Backfill existing products ---
    if update_products:
        # Bulk-delete all child rows for affected product IDs in one pass each
        product_ids = [pid for pid, _, _ in update_products]

        for table, fk in [
            (ProductLink.__table__, "product_id"),
            (ProductTeamMember.__table__, "product_id"),
            (ProductBacker.__table__, "product_id"),
            (ProductCategory.__table__, "product_id"),
            (ProductVoice.__table__, "product_id"),
        ]:
            await session.execute(
                delete(table).where(table.c[fk].in_(product_ids))
            )

        await session.flush()

        for product_id, parsed, existing_logo in update_products:
            # Update scalar fields — preserve name, slug, logo
            await session.execute(
                Product.__table__.update()
                .where(Product.__table__.c.id == product_id)
                .values(
                    short_desc=parsed["short_desc"],
                    desc=parsed["description"],
                    stage=parsed["stage"].value if parsed["stage"] else None,
                    founded=parsed["founded"],
                    quality_badge=parsed["quality_badge"],
                    email=parsed["email"],
                )
            )
            _insert_child_rows(session, product_id, parsed, category_id_by_name)

        log.info("  [products] backfilled %d existing products", len(update_products))
    else:
        log.info("  [products] no existing products to backfill")


def _parse_row(row: dict) -> dict:
    """Extract and normalise all fields from a CSV row."""
    raw_stage = row.get("stage", "").strip().lower()
    raw_year = row.get("founded", "").strip()

    raw_cat = row.get("category", "").strip()
    raw_cat = CATEGORY_ALIASES.get(raw_cat, raw_cat) if raw_cat else None

    return {
        "short_desc":    row.get("short_desc", "").strip() or None,
        "description":   row.get("description", "").strip() or None,
        "stage":         _STAGE_MAP.get(raw_stage),
        "founded":       int(raw_year) if raw_year.isdigit() else None,
        "quality_badge": row.get("quality_badge", "").strip() or None,
        "email":         row.get("email", "").strip() or None,
        # Links
        "twitter":       row.get("twitter", "").strip() or None,
        "website":       row.get("website", "").strip() or None,
        "discord":       row.get("discord", "").strip() or None,
        "docs":          row.get("docs", "").strip() or None,
        "github":        row.get("github", "").strip() or None,
        "other_link":    row.get("other link", "").strip() or None,
        # Multi-value
        "press_urls":    _parse_press_urls(row.get("voices", "")),
        "team":          _parse_team(row.get("team", "")),
        "backers":       _parse_backers(row.get("backers", "")),
        # Categories
        "category":      raw_cat,
        "subcategories": _split(row.get("subcategory", ""), ";"),
    }


def _insert_child_rows(
    session: AsyncSession,
    product_id: int,
    parsed: dict,
    category_id_by_name: dict[str, int],
) -> None:
    """Insert all child rows for one product after the product row exists."""
    # Links
    _add_link(session, product_id, ProductLinkType.WEBSITE, parsed["website"])
    _add_link(session, product_id, ProductLinkType.GITHUB,  parsed["github"])
    _add_link(session, product_id, ProductLinkType.TWITTER, parsed["twitter"])
    _add_link(session, product_id, ProductLinkType.DISCORD, parsed["discord"])
    _add_link(session, product_id, ProductLinkType.DOCS,    parsed["docs"])
    _add_link(session, product_id, ProductLinkType.OTHER,   parsed["other_link"])
    for sort, url in enumerate(parsed["press_urls"], start=10):
        session.add(ProductVoice(
            product_id=product_id,
            source_url=url,
            quote="",
            author_handle="",
            sort_order=sort * 10,
        ))

    # Team members
    for member in parsed["team"]:
        if not member["name"]:
            continue
        session.add(ProductTeamMember(
            product_id=product_id,
            name=member["name"],
            role_label=member["role_label"],
            bio_note=member["bio_note"],
            linkedin_url=member["linkedin_url"],
            twitter_url=member["twitter_url"],
            github_url=member["github_url"],
            other_url=member["other_url"],
            status=VerificationStatus.APPROVED,
        ))

    # Backers
    for backer_name in parsed["backers"]:
        session.add(ProductBacker(product_id=product_id, name=backer_name))

    # Categories: parent first, then subcategories
    cat_names_to_link: list[str] = []
    if parsed["category"]:
        cat_names_to_link.append(parsed["category"])
    for sub in parsed["subcategories"]:
        if sub in category_id_by_name:
            cat_names_to_link.append(sub)

    _link_categories(
        session, product_id, cat_names_to_link,
        category_id_by_name, ProductCategory, "product_id", "products",
    )


def _add_link(
    session: AsyncSession,
    product_id: int,
    link_type: ProductLinkType,
    url: str | None,
) -> None:
    if url:
        session.add(ProductLink(product_id=product_id, link_type=link_type, url=url))


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
