"""
Backfill Logo.dev logos for already-submitted products that are still pending,
have a website link, and have no logo set yet.

Usage:
    PYTHONPATH=. python scripts/backfill_logos.py [--dry-run] [--concurrency N]
"""

import argparse
import asyncio
import logging

from sqlalchemy import select

from app.common.storage import R2StorageService
from app.common.validators import extract_domain
from app.database.connection import db_manager
from app.domain.product.model import Product, ProductLink
from app.domain.user.model import User  # noqa: F401 — registers 'users' table in metadata
from app.enums.enums import ProductLinkType, ProductStatus
from app.exceptions.exceptions import ExternalServiceError
from app.infrastructure.logodev.service import LogoDevService, is_logo_skip_domain

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

DEFAULT_CONCURRENCY = 5


async def _fetch_candidates(session) -> list[tuple[int, str, str]]:
    """(product_id, slug, website_url) for pending products with a website link and no logo."""
    result = await session.execute(
        select(Product.id, Product.slug, ProductLink.url)
        .join(ProductLink, ProductLink.product_id == Product.id)
        .where(
            Product.status == ProductStatus.PENDING,
            Product.logo.is_(None),
            Product.deleted_at.is_(None),
            ProductLink.link_type == ProductLinkType.WEBSITE,
        )
    )
    return [(row.id, row.slug, row.url) for row in result.all()]


async def _process_one(
    product_id: int,
    slug: str,
    website_url: str,
    logo_dev: LogoDevService,
    storage: R2StorageService,
    dry_run: bool,
) -> str:
    """Returns one of: 'set', 'no_logo', 'invalid_domain', 'skipped_domain', 'error'."""
    domain = extract_domain(website_url)
    if not domain:
        log.info("  SKIP    %-30s invalid website URL: %s", slug, website_url)
        return "invalid_domain"
    if is_logo_skip_domain(domain):
        log.info("  SKIP    %-30s skipped platform domain: %s", slug, domain)
        return "skipped_domain"

    try:
        result = await logo_dev.fetch_logo(domain)
    except ExternalServiceError as exc:
        log.warning("  ERROR   %-30s %s: %s", slug, domain, exc)
        return "error"

    if result is None:
        log.info("  NONE    %-30s no logo for %s", slug, domain)
        return "no_logo"

    data, content_type = result
    if dry_run:
        log.info("  WOULD SET %-28s %s (%d bytes)", slug, domain, len(data))
        return "set"

    async with db_manager.session_scope() as session:
        product = await session.get(Product, product_id)
        if product is None or product.logo:
            return "no_logo"  # deleted or raced with a manual upload since we listed it
        key = storage.build_storage_key(slug, f"{domain}.webp", subfolder="logo")
        await storage.upload_file(key=key, data=data, content_type=content_type)
        product.logo = key
        await session.commit()

    log.info("  SET     %-30s %s", slug, domain)
    return "set"


async def backfill_logos(dry_run: bool, concurrency: int) -> None:
    db_manager.init_engine()
    logo_dev = LogoDevService()
    storage = R2StorageService()

    async with db_manager.session_scope() as session:
        candidates = await _fetch_candidates(session)

    log.info("%d pending product(s) with a website link and no logo\n", len(candidates))
    if not candidates:
        await db_manager.close()
        return

    semaphore = asyncio.Semaphore(concurrency)

    async def _bounded(product_id: int, slug: str, url: str) -> str:
        async with semaphore:
            return await _process_one(product_id, slug, url, logo_dev, storage, dry_run)

    results = await asyncio.gather(
        *(_bounded(pid, slug, url) for pid, slug, url in candidates)
    )

    await db_manager.close()

    counts = {outcome: results.count(outcome) for outcome in set(results)}
    log.info(
        "\nDone — set: %d  no_logo: %d  invalid_domain: %d  skipped_domain: %d  error: %d",
        counts.get("set", 0),
        counts.get("no_logo", 0),
        counts.get("invalid_domain", 0),
        counts.get("skipped_domain", 0),
        counts.get("error", 0),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill Logo.dev logos for pending products")
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading or writing to the DB")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Max concurrent Logo.dev requests")
    args = parser.parse_args()
    asyncio.run(backfill_logos(dry_run=args.dry_run, concurrency=args.concurrency))
