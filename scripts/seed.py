"""
Seed script for AthenaX database.

Usage:
    make seed
"""

import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import db_manager
from app.domain.category.model import Category
from app.domain.lab.model import Lab, LabCategory
from app.domain.university.model import University

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

CATEGORIES: list[str] = [
    "AI & Agents",
    "Robotics",
    "Biotech",
    "Crypto & DeFi",
    "Developer Tools",
    "Infrastructure",
    "Climate & Energy",
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

    Fetches existing names, inserts only the missing ones via `build(name)`,
    flushes, then returns {name: id} for every row.
    """
    existing = set((await session.execute(select(name_col))).scalars().all())
    new_names = [n for n in names if n not in existing]

    if new_names:
        for name in new_names:
            session.add(build(name))
        await session.flush()
        log.info("  [%s] seeded %d: %s", label, len(new_names), new_names)
    else:
        log.info("  [%s] all present, skipping", label)

    rows = (await session.execute(select(id_col, name_col))).all()
    return {name: row_id for row_id, name in rows}


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
    seeded: list[str] = []

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
        await session.flush()  # populate new_lab.id before inserting associations

        for cat_name in lab["categories"]:
            cat_id = category_id_by_name.get(cat_name)
            if cat_id is None:
                log.warning(
                    "  [labs] unknown category %r for lab %r — skipping association",
                    cat_name, lab["name"],
                )
                continue
            session.add(LabCategory(lab_id=new_lab.id, category_id=cat_id))

        seeded.append(lab["name"])

    if seeded:
        log.info("  [labs] seeded %d: %s", len(seeded), seeded)
    else:
        log.info("  [labs] all present, skipping")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    log.info("Starting seed…")
    db_manager.init_engine()

    async with db_manager.session_scope() as session:
        category_id_by_name = await seed_categories(session)
        university_id_by_name = await seed_universities(session)
        await seed_labs(session, university_id_by_name, category_id_by_name)
        await session.commit()

    await db_manager.close()
    log.info("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
