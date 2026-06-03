"""
Seed load-test data into the local dev database.

Inserts:
  - 10 test users per role (USER / INVESTOR / ADMIN) with email-verified flag set
  - 1 000 products (category + subcategory) with skewed comments/voices/backers
  - 200 articles and 200 broadcasts

Usage:
    .venv/bin/python scripts/seed_load_data.py
    .venv/bin/python scripts/seed_load_data.py --products 2000 --articles 300 --broadcasts 300
    .venv/bin/python scripts/seed_load_data.py --wipe   # delete all seeded rows first

The script is idempotent: rows with emails/slugs that already exist are skipped.
Test-user password is read from LOAD_TEST_USER_PASSWORD (default: Testpass1!).
"""

import argparse
import asyncio
import logging
import random
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.database.connection import db_manager
from app.domain.article.model import Article
from app.domain.broadcast.model import Broadcast
from app.domain.category.model import Category
from app.domain.product.model import Product, ProductBacker, ProductCategory, ProductComment, ProductLink, ProductVoice
from app.domain.user.model import User
from app.enums.enums import (
    ArticleStatus,
    ArticleType,
    BroadcastStatus,
    BroadcastType,
    ProductLinkType,
    ProductStage,
    ProductStatus,
    UserRole,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fake data pools
# ---------------------------------------------------------------------------

_ADJECTIVES = [
    "Adaptive", "Autonomous", "Convergent", "Decentralised", "Emergent",
    "Frictionless", "Generative", "Hyper", "Intelligent", "Kinetic",
    "Latent", "Modular", "Neural", "Open", "Permissionless",
    "Quantum", "Recursive", "Scalable", "Trustless", "Unified",
    "Verifiable", "Warp", "Zero-Knowledge", "Ambient", "Composable",
]
_NOUNS = [
    "Atlas", "Beacon", "Cipher", "Drift", "Echo",
    "Flux", "Grid", "Helix", "Index", "Junction",
    "Kernel", "Layer", "Mesh", "Nexus", "Orbit",
    "Prism", "Relay", "Signal", "Tensor", "Vault",
    "Wormhole", "Apex", "Bridge", "Core", "Datum",
]
_SUFFIXES = [
    "AI", "Labs", "Protocol", "Network", "Systems",
    "IO", "Hub", "Base", "Chain", "Stack",
    "", "", "",  # weight towards no suffix
]

_PARENT_CATEGORIES = [
    ("AI & Agents", ["Language Models", "Autonomous Agents", "Computer Vision", "Speech AI"]),
    ("Biotech", ["Genomics", "Drug Discovery", "Synthetic Biology", "Med Devices"]),
    ("Crypto", ["DeFi", "NFTs", "Layer 2", "DAOs", "ZK Proofs"]),
    ("Developer Tools", ["CI/CD", "Observability", "API Tooling", "Low Code"]),
    ("Infrastructure", ["Cloud Native", "Edge Computing", "Storage", "Networking"]),
    ("Robotics", ["Industrial", "Consumer", "Drone Tech", "Surgical Robots"]),
]

_STAGES = list(ProductStage)
_ARTICLE_TYPES = list(ArticleType)
_BROADCAST_TYPES = list(BroadcastType)

_SHORT_DESCS = [
    "The fastest way to deploy {noun} infrastructure at scale.",
    "Bringing {adj} intelligence to everyday {noun} workflows.",
    "{adj} {noun} solutions for the next generation of builders.",
    "Rethinking {noun} with {adj} AI-powered tooling.",
    "Open-source {adj} {noun} for distributed teams.",
]

_ARTICLE_TITLES = [
    "Why {adj} AI Is Reshaping the {noun} Landscape",
    "The Rise of {adj} {noun}: What You Need to Know",
    "Inside the {adj} {noun} Revolution",
    "How {adj} {noun} Is Changing Everything",
    "{noun} Meets {adj} AI: A Deep Dive",
    "Building {adj} {noun} Systems at Scale",
    "The Future of {adj} {noun} Infrastructure",
    "Understanding {adj} {noun} Protocols",
]

_BROADCAST_TITLES = [
    "{adj} {noun} Summit 2024 — Keynote",
    "Live: {adj} {noun} Protocol Launch",
    "Roundtable: The State of {adj} {noun}",
    "{noun} Whitepaper Breakdown — {adj} Edition",
    "Office Hours: Building with {adj} {noun}",
    "AMA — {adj} {noun} Team",
]


def _slug(name: str) -> str:
    s = re.sub(r"[^\w\s-]", "", name.lower().strip())
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s[:255]


def _fake_name(i: int) -> str:
    adj = _ADJECTIVES[i % len(_ADJECTIVES)]
    noun = _NOUNS[(i * 7 + 3) % len(_NOUNS)]
    suffix = _SUFFIXES[(i * 13) % len(_SUFFIXES)]
    parts = [adj, noun]
    if suffix:
        parts.append(suffix)
    return " ".join(parts)


def _fake_product_name(i: int) -> str:
    return _fake_name(i)


def _fill(template: str, i: int) -> str:
    adj = _ADJECTIVES[i % len(_ADJECTIVES)]
    noun = _NOUNS[(i * 11 + 5) % len(_NOUNS)]
    return template.format(adj=adj, noun=noun)


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

async def _ensure_categories(session) -> dict[tuple[str, int | None], int]:
    """Upsert the fixed category tree, return (name, parent_id) → id map."""
    result = await session.execute(select(Category.id, Category.name, Category.parent_id))
    existing: dict[tuple[str, int | None], int] = {
        (name, pid): cid for cid, name, pid in result.all()
    }

    # Parents first
    for parent_name, _ in _PARENT_CATEGORIES:
        if (parent_name, None) not in existing:
            cat = Category(name=parent_name, status="approved")
            session.add(cat)

    await session.flush()

    # Re-fetch to get new IDs
    result = await session.execute(select(Category.id, Category.name, Category.parent_id))
    existing = {(name, pid): cid for cid, name, pid in result.all()}

    # Subcategories
    for parent_name, subs in _PARENT_CATEGORIES:
        parent_id = existing.get((parent_name, None))
        if parent_id is None:
            continue
        for sub_name in subs:
            if (sub_name, parent_id) not in existing:
                session.add(Category(name=sub_name, parent_id=parent_id, status="approved"))

    await session.flush()

    result = await session.execute(select(Category.id, Category.name, Category.parent_id))
    existing = {(name, pid): cid for cid, name, pid in result.all()}
    log.info("[categories] %d rows in DB", len(existing))
    return existing


async def _seed_products(session, count: int, category_map: dict) -> None:
    result = await session.execute(select(Product.slug))
    existing_slugs: set[str] = set(result.scalars().all())

    # Build a flat list of (parent_cat_id, sub_cat_id) pairs for assignment
    pairs: list[tuple[int, int]] = []
    for parent_name, subs in _PARENT_CATEGORIES:
        parent_id = category_map.get((parent_name, None))
        if parent_id is None:
            continue
        for sub_name in subs:
            sub_id = category_map.get((sub_name, parent_id))
            if sub_id:
                pairs.append((parent_id, sub_id))

    if not pairs:
        log.error("[products] no category pairs found — cannot seed products")
        return

    now = datetime.now(timezone.utc)
    added = 0

    for i in range(count):
        name = _fake_product_name(i)
        slug = _slug(name)
        if slug in existing_slugs:
            # Make unique with a numeric suffix
            slug = f"{slug}-{i}"
        if slug in existing_slugs:
            continue
        existing_slugs.add(slug)

        tmpl = _SHORT_DESCS[i % len(_SHORT_DESCS)]
        short_desc = _fill(tmpl, i)
        stage = _STAGES[i % len(_STAGES)]
        parent_id, sub_id = pairs[i % len(pairs)]

        # First 50 get recent timestamps so they surface first on the default
        # "newest" sort and become the hot-ID set in the load-test cache.
        if i < 50:
            created_at = now - timedelta(minutes=i * 10)
        elif i < 250:
            created_at = now - timedelta(days=random.randint(7, 60))
        else:
            created_at = now - timedelta(days=random.randint(60, 365))

        product = Product(
            slug=slug,
            name=name,
            short_desc=short_desc,
            stage=stage,
            founded=2018 + (i % 7),
            imported=True,
            status=ProductStatus.APPROVED,
            created_by_id=None,
            created_at=created_at,
        )
        session.add(product)
        added += 1

        # We need the product ID after flush — batch in chunks of 100
        if added % 100 == 0:
            await session.flush()
            # Link categories + add a website link for recently flushed products
            result2 = await session.execute(
                select(Product.id, Product.slug).where(
                    Product.slug.in_(list(existing_slugs))
                )
            )
            id_by_slug: dict[str, int] = {s: pid for pid, s in result2.all()}
            # We'll do linking after final flush below; just continue for now

    await session.flush()

    # Fetch all product IDs we just created (not just the last batch)
    result3 = await session.execute(
        select(Product.id, Product.slug).where(Product.slug.in_(list(existing_slugs)))
    )
    id_by_slug: dict[str, int] = {s: pid for pid, s in result3.all()}

    # Fetch existing category links to avoid duplicates
    existing_links_result = await session.execute(
        select(ProductCategory.product_id, ProductCategory.category_id)
    )
    existing_links: set[tuple[int, int]] = set(existing_links_result.all())

    existing_product_links_result = await session.execute(
        select(ProductLink.product_id)
    )
    products_with_link: set[int] = set(existing_product_links_result.scalars().all())

    i = 0
    for slug, pid in id_by_slug.items():
        parent_id, sub_id = pairs[i % len(pairs)]
        i += 1

        if (pid, parent_id) not in existing_links:
            session.add(ProductCategory(product_id=pid, category_id=parent_id))
            existing_links.add((pid, parent_id))
        if (pid, sub_id) not in existing_links:
            session.add(ProductCategory(product_id=pid, category_id=sub_id))
            existing_links.add((pid, sub_id))

        if pid not in products_with_link:
            session.add(ProductLink(
                product_id=pid,
                link_type=ProductLinkType.WEBSITE,
                url=f"https://example.com/{slug}",
            ))
            products_with_link.add(pid)

    await session.flush()
    log.info("[products] seeded %d products", added)


async def _seed_articles(session, count: int) -> None:
    result = await session.execute(select(Article.slug))
    existing_slugs: set[str] = set(result.scalars().all())

    now = datetime.now(timezone.utc)
    added = 0

    for i in range(count):
        tmpl = _ARTICLE_TITLES[i % len(_ARTICLE_TITLES)]
        title = _fill(tmpl, i)
        slug = _slug(title)
        if slug in existing_slugs:
            slug = f"{slug}-{i}"
        if slug in existing_slugs:
            continue
        existing_slugs.add(slug)

        pub_at = now - timedelta(days=random.randint(0, 180))
        session.add(Article(
            title=title,
            slug=slug,
            content=f"<p>{title}. " + ("Lorem ipsum dolor sit amet. " * 10) + "</p>",
            status=ArticleStatus.PUBLISHED,
            article_type=_ARTICLE_TYPES[i % len(_ARTICLE_TYPES)],
            published_at=pub_at,
            created_by_id=None,
        ))
        added += 1

    await session.flush()
    log.info("[articles] seeded %d articles", added)


async def _seed_broadcasts(session, count: int) -> None:
    result = await session.execute(select(Broadcast.slug))
    existing_slugs: set[str] = set(result.scalars().all())

    now = datetime.now(timezone.utc)
    added = 0

    for i in range(count):
        tmpl = _BROADCAST_TITLES[i % len(_BROADCAST_TITLES)]
        title = _fill(tmpl, i)
        slug = _slug(title)
        if slug in existing_slugs:
            slug = f"{slug}-{i}"
        if slug in existing_slugs:
            continue
        existing_slugs.add(slug)

        pub_at = now - timedelta(days=random.randint(0, 180))
        session.add(Broadcast(
            title=title,
            slug=slug,
            description=f"{title} — a deep dive into the topic.",
            broadcast_type=_BROADCAST_TYPES[i % len(_BROADCAST_TYPES)],
            status=BroadcastStatus.PUBLISHED,
            published_at=pub_at,
            origin_date=pub_at,
            created_by_id=None,
        ))
        added += 1

    await session.flush()
    log.info("[broadcasts] seeded %d broadcasts", added)


_COMMENT_TEXTS = [
    "This is a game changer for the space.",
    "Really impressive work from the team.",
    "Would love to see more documentation here.",
    "The architecture is surprisingly solid.",
    "Needs better onboarding but the core is strong.",
    "Following this closely — huge potential.",
    "Any timeline on the mainnet launch?",
    "The tokenomics need more thought.",
    "Excited to see where this goes.",
    "Strong team, strong thesis.",
]
_VOICE_DATA = [
    ("The future of decentralised finance.", "@vitalik"),
    ("This solves a real problem at scale.", "@naval"),
    ("Worth watching closely.", "@balajis"),
    ("Impressed by the technical depth here.", "@pmarca"),
    ("One of the most thoughtful teams I've seen.", "@elad"),
]
_BACKER_NAMES = [
    "a16z", "Paradigm", "Sequoia", "Coinbase Ventures",
    "Binance Labs", "Pantera Capital", "Electric Capital",
    "Multicoin Capital", "Framework Ventures", "1kx",
]


async def _seed_test_users(session, password: str) -> None:
    """Upsert 10 users per role (USER, INVESTOR, ADMIN) with email-verified flag set."""
    from app.utils.oauth2 import hash_password

    result = await session.execute(select(User.email))
    existing_emails: set[str] = set(result.scalars().all())

    roles = [
        (UserRole.USER,     "load-user"),
        (UserRole.INVESTOR, "load-investor"),
        (UserRole.ADMIN,    "load-admin"),
    ]
    password_hash = hash_password(password)
    added = 0
    for role, prefix in roles:
        for n in range(1, 11):
            email = f"{prefix}-{n:02d}@test.athena"
            if email in existing_emails:
                continue
            session.add(User(
                name=f"Load Tester {n:02d}",
                email=email,
                password_hash=password_hash,
                verified=True,
                role=role,
            ))
            added += 1

    await session.flush()
    log.info("[test-users] seeded %d users  password=%s", added, password)


async def _seed_comments_voices_backers(session) -> None:
    """Seed skewed child data: hot products (first 50 by newest) get many, rest get few."""
    # Find a user to own seeded comments (created_by_id must be non-null in CommentOutSchema)
    result = await session.execute(
        select(User.id).where(User.email.like("load-admin-%@test.athena")).limit(1)
    )
    commenter_id = result.scalar_one_or_none()
    if commenter_id is None:
        result = await session.execute(select(User.id).limit(1))
        commenter_id = result.scalar_one_or_none()
    if commenter_id is None:
        log.warning("[skew-data] no users found — skipping comment seeding")
        return

    result = await session.execute(
        select(Product.id)
        .where(Product.imported.is_(True))
        .order_by(Product.created_at.desc())
    )
    product_ids = list(result.scalars().all())
    if not product_ids:
        return

    hot  = product_ids[:50]
    warm = product_ids[50:250]
    cold = product_ids[250:]

    existing_comments = set((await session.execute(select(ProductComment.product_id))).scalars().all())
    existing_voices   = set((await session.execute(select(ProductVoice.product_id))).scalars().all())
    existing_backers  = set((await session.execute(select(ProductBacker.product_id))).scalars().all())

    c_added = v_added = b_added = 0

    for pid_list, comment_range, voice_count, backer_count in [
        (hot,  (20, 40), 4, 5),
        (warm, (3,  8),  2, 2),
        (cold, (0,  2),  0, 0),
    ]:
        for pid in pid_list:
            if pid not in existing_comments:
                for j in range(random.randint(*comment_range)):
                    session.add(ProductComment(
                        product_id=pid,
                        text=_COMMENT_TEXTS[j % len(_COMMENT_TEXTS)],
                        pinned=False,
                        created_by_id=commenter_id,
                    ))
                    c_added += 1

            if pid not in existing_voices and voice_count > 0:
                for j in range(voice_count):
                    quote, handle = _VOICE_DATA[j % len(_VOICE_DATA)]
                    session.add(ProductVoice(
                        product_id=pid,
                        quote=quote,
                        author_handle=handle,
                        sort_order=(j + 1) * 10,
                    ))
                v_added += voice_count

            if pid not in existing_backers and backer_count > 0:
                for j in range(backer_count):
                    session.add(ProductBacker(
                        product_id=pid,
                        name=_BACKER_NAMES[j % len(_BACKER_NAMES)],
                    ))
                b_added += backer_count

    await session.flush()
    log.info("[skew-data] %d comments  %d voices  %d backers", c_added, v_added, b_added)


async def _wipe(session) -> None:
    from sqlalchemy import delete as sa_delete

    log.info("[wipe] deleting seeded data …")
    await session.execute(sa_delete(ProductComment))
    await session.execute(sa_delete(ProductVoice))
    await session.execute(sa_delete(ProductBacker))
    await session.execute(sa_delete(ProductCategory))
    await session.execute(sa_delete(ProductLink))
    await session.execute(
        sa_delete(Product).where(Product.imported.is_(True))
    )
    await session.execute(sa_delete(Article))
    await session.execute(sa_delete(Broadcast))
    await session.execute(
        sa_delete(User).where(User.email.like("load-%@test.athena"))
    )
    await session.flush()
    log.info("[wipe] done")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main(products: int, articles: int, broadcasts: int, wipe: bool, password: str) -> None:
    db_manager.init_engine()

    async with db_manager.session_scope() as session:
        if wipe:
            await _wipe(session)

        await _seed_test_users(session, password)
        category_map = await _ensure_categories(session)
        await _seed_products(session, products, category_map)
        await _seed_comments_voices_backers(session)
        await _seed_articles(session, articles)
        await _seed_broadcasts(session, broadcasts)

        await session.commit()

    await db_manager.close()
    log.info("Done.")


if __name__ == "__main__":
    import os
    parser = argparse.ArgumentParser(description="Seed load-test data into the local dev DB")
    parser.add_argument("--products",   type=int, default=1000)
    parser.add_argument("--articles",   type=int, default=200)
    parser.add_argument("--broadcasts", type=int, default=200)
    parser.add_argument("--wipe", action="store_true", help="Delete all seeded rows first")
    parser.add_argument(
        "--password",
        default=os.getenv("LOAD_TEST_USER_PASSWORD", "Testpass1!"),
        help="Password for seeded test users (env: LOAD_TEST_USER_PASSWORD)",
    )
    args = parser.parse_args()

    asyncio.run(main(
        products=args.products,
        articles=args.articles,
        broadcasts=args.broadcasts,
        wipe=args.wipe,
        password=args.password,
    ))
